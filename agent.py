"""AI Code Agent — LangChain 1.x orchestrator with tools, memory, and Claude API.

Features:
- ReAct agent with 4 tools (code_gen, review, test_gen, commit)
- SQLite-backed persistent conversation memory
- Exponential backoff retry for API rate limits
- Request-level caching to avoid redundant API calls
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from langchain.agents import create_agent as create_langchain_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from config import DEFAULT_CONFIG, AgentConfig
from prompts.templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_llm: ChatAnthropic | None = None
_agent: CompiledStateGraph | None = None
_checkpointer: SqliteSaver | None = None
_thread_id: str = "default"

# ── Simple disk cache for LLM responses ──
_cache_dir = Path("./.agent_cache")
_cache_dir.mkdir(exist_ok=True)


def _cache_key(prompt: str, model: str) -> str:
    """Generate a deterministic cache key from prompt + model."""
    return hashlib.sha256(f"{model}::{prompt}".encode()).hexdigest()[:16]


def _cache_get(prompt: str, model: str, ttl: int = 3600) -> str | None:
    """Return cached response if not expired (TTL in seconds, default 1h)."""
    key = _cache_key(prompt, model)
    cache_file = _cache_dir / f"{key}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) < ttl:
                return data.get("response")
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def _cache_set(prompt: str, model: str, response: str) -> None:
    """Store a response in the disk cache."""
    key = _cache_key(prompt, model)
    cache_file = _cache_dir / f"{key}.json"
    cache_file.write_text(
        json.dumps({"ts": time.time(), "response": response}, ensure_ascii=False),
        encoding="utf-8",
    )


def _retry_llm_call(llm: ChatAnthropic, prompt: str, max_retries: int = 3) -> Any:
    """Call LLM with exponential backoff retry on rate-limit errors.

    Retries on: connection errors, timeout, 429 (rate limit), 5xx.
    Max backoff: 32 seconds.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            is_retryable = any(kw in msg for kw in (
                "rate", "limit", "timeout", "connection", "429", "500", "502", "503", "504"
            ))
            if not is_retryable or attempt >= max_retries:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning("LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                          attempt + 1, max_retries + 1, exc, wait)
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def invoke_llm(prompt: str, use_cache: bool = True) -> str:
    """Invoke the LLM with retry, caching, and error handling.

    Args:
        prompt: The complete prompt text to send.
        use_cache: Whether to check/update the disk cache.

    Returns:
        The LLM's text response content.
    """
    llm = get_llm()
    model = DEFAULT_CONFIG.llm.model

    # Check cache
    if use_cache:
        cached = _cache_get(prompt, model)
        if cached is not None:
            logger.debug("Cache hit for prompt hash %s", _cache_key(prompt, model))
            return cached

    # Call with retry
    start = time.time()
    response = _retry_llm_call(llm, prompt)
    elapsed = time.time() - start
    logger.debug("LLM call completed in %.1fs", elapsed)

    # Extract content
    raw = response.content if hasattr(response, "content") else str(response)
    if isinstance(raw, list):
        raw = "".join(
            block.get("text", "") if isinstance(block, dict) and block.get("type") != "thinking" else ""
            for block in raw
        )

    # Update cache
    if use_cache:
        _cache_set(prompt, model, raw)

    return raw


def get_llm() -> ChatAnthropic:
    """Get or create the global LLM instance.

    Raises:
        RuntimeError: If no API key has been configured (either via environment
                      variable or reconfigure_llm()).
    """
    global _llm
    if _llm is None:
        cfg = DEFAULT_CONFIG.llm
        api_key = cfg.api_key
        if not api_key:
            raise RuntimeError(
                "未配置 API Key。请在 GUI ⚙️ 设置中填入 API Key 并点击「✅ 连接」，"
                "或设置环境变量 ANTHROPIC_API_KEY"
            )
        _llm = ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=cfg.base_url,
            api_key=api_key,
        )
    return _llm


def reconfigure_llm(
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatAnthropic:
    """Reconfigure the global LLM with new settings (e.g. from GUI).

    After calling this, the next get_llm() or create_agent() call will use
    the updated configuration.  Existing agent instances should be re-created
    via create_agent() after reconfiguration.

    Args:
        api_key: New API key. Empty string = keep current.
        model: New model name. Empty string = keep current.
        base_url: New base URL. Empty string = keep current.
        temperature: New temperature. None = keep current.
        max_tokens: New max_tokens. None = keep current.

    Returns:
        The newly created ChatAnthropic instance.
    """
    global _llm, _agent
    cfg = DEFAULT_CONFIG.llm
    resolved_key = api_key or cfg.api_key
    if not resolved_key:
        raise RuntimeError("未提供 API Key，无法配置模型")
    _llm = ChatAnthropic(
        model=model or cfg.model,
        temperature=temperature if temperature is not None else cfg.temperature,
        max_tokens=max_tokens if max_tokens is not None else cfg.max_tokens,
        base_url=base_url or cfg.base_url,
        api_key=resolved_key,
    )
    _agent = None  # force re-creation on next use
    return _llm


def get_checkpointer() -> SqliteSaver:
    """Get or create the SQLite checkpointer for persistent memory."""
    global _checkpointer
    if _checkpointer is None:
        db_path = Path(DEFAULT_CONFIG.memory_file).with_suffix(".db")
        _checkpointer = SqliteSaver.from_conn_string(str(db_path))
    return _checkpointer


def create_agent(config: AgentConfig | None = None) -> CompiledStateGraph:
    """Build the agent with all tools, checkpointer-based memory, and system prompt.

    Args:
        config: Optional agent configuration. Uses DEFAULT_CONFIG if not provided.

    Returns:
        Compiled LangGraph agent (CompiledStateGraph).
    """
    global _agent, _llm

    cfg = config or DEFAULT_CONFIG

    _llm = ChatAnthropic(
        model=cfg.llm.model,
        temperature=cfg.llm.temperature,
        max_tokens=cfg.llm.max_tokens,
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key or None,
    )

    from tools.code_interpreter import code_interpreter
    from tools.static_reviewer import static_reviewer
    from tools.git_commit import git_commit
    from tools.test_generator import test_generator

    tools = [code_interpreter, static_reviewer, git_commit, test_generator]
    checkpointer = get_checkpointer()

    _agent = create_langchain_agent(
        model=_llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return _agent


def get_agent() -> CompiledStateGraph:
    """Get the current agent, creating one if needed."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def run(input_text: str, thread_id: str | None = None) -> dict[str, Any]:
    """Run the agent with a natural language input.

    Args:
        input_text: User's natural language request.
        thread_id: Conversation thread ID for multi-turn memory.
                   Uses the global default if not provided.

    Returns:
        Agent response dict with 'output' extracted from messages.
    """
    global _thread_id
    tid = thread_id or _thread_id
    _thread_id = tid

    agent_executor = get_agent()
    result = agent_executor.invoke(
        {"messages": [{"role": "user", "content": input_text}]},
        config={"configurable": {"thread_id": tid}},
    )

    # Extract the last AI message as the output
    messages = result.get("messages", [])
    output = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.type == "ai":
            output = msg.content
            break

    return {"output": output, "messages": messages}


def run_with_messages(messages: list[dict[str, str]], thread_id: str | None = None) -> dict[str, Any]:
    """Run the agent with a pre-built message list.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        thread_id: Conversation thread ID.

    Returns:
        Agent response dict with 'output' and 'messages'.
    """
    global _thread_id
    tid = thread_id or _thread_id
    _thread_id = tid

    agent_executor = get_agent()
    result = agent_executor.invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": tid}},
    )

    msgs = result.get("messages", [])
    output = ""
    for msg in reversed(msgs):
        if hasattr(msg, "content") and msg.type == "ai":
            output = msg.content
            break

    return {"output": output, "messages": msgs}


def reset_agent(thread_id: str | None = None) -> None:
    """Reset the agent — clears conversation history, checkpointer, and memory backups."""
    global _agent, _llm, _checkpointer
    _agent = None
    _llm = None
    _checkpointer = None

    import os

    # Clean up SQLite checkpointer DB
    db_path = Path(DEFAULT_CONFIG.memory_file).with_suffix(".db")
    if db_path.exists():
        try:
            os.remove(db_path)
        except OSError:
            pass

    # Clean up WAL and SHM files that SQLite may leave behind
    for suffix in (".db-wal", ".db-shm"):
        wal_path = db_path.with_suffix(suffix)
        if wal_path.exists():
            try:
                os.remove(wal_path)
            except OSError:
                pass

    # Clean up SessionMemory JSON backup
    json_path = Path(DEFAULT_CONFIG.memory_file)
    if json_path.exists():
        try:
            os.remove(json_path)
        except OSError:
            pass


def set_thread_id(tid: str) -> None:
    """Set the global thread ID for conversation memory."""
    global _thread_id
    _thread_id = tid


def clear_cache(older_than: int = 0) -> int:
    """Clear the LLM response cache.

    Args:
        older_than: If > 0, only clear entries older than this many seconds.

    Returns:
        Number of cache entries removed.
    """
    removed = 0
    cutoff = time.time() - older_than if older_than > 0 else float("inf")
    for cache_file in _cache_dir.glob("*.json"):
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if data.get("ts", 0) < cutoff:
                cache_file.unlink()
                removed += 1
        except (json.JSONDecodeError, OSError):
            cache_file.unlink(missing_ok=True)
            removed += 1
    return removed


def cache_stats() -> dict[str, Any]:
    """Return cache statistics."""
    files = list(_cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "entries": len(files),
        "size_bytes": total_size,
        "size_kb": round(total_size / 1024, 1),
        "directory": str(_cache_dir.resolve()),
    }
