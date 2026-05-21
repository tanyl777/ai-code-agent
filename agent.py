"""AI Code Agent — LangChain 1.x orchestrator with tools, memory, and Claude API."""

import logging
from pathlib import Path
from typing import Any

from langchain.agents import create_agent as create_langchain_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from config import DEFAULT_CONFIG, AgentConfig
from prompts.templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_llm: ChatAnthropic | None = None
_agent: CompiledStateGraph | None = None
_checkpointer: SqliteSaver | None = None
_thread_id: str = "default"


def get_llm() -> ChatAnthropic:
    """Get or create the global LLM instance."""
    global _llm
    if _llm is None:
        cfg = DEFAULT_CONFIG.llm
        _llm = ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=cfg.base_url,
            api_key=cfg.api_key or None,
        )
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

    tools = [code_interpreter, static_reviewer, git_commit]
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
    """Reset the agent — clears conversation history for the thread."""
    global _agent, _llm
    _agent = None
    _llm = None
    # New checkpointer will be created on next use, old DB can be deleted
    import os
    db_path = Path(DEFAULT_CONFIG.memory_file).with_suffix(".db")
    if db_path.exists():
        os.remove(db_path)


def set_thread_id(tid: str) -> None:
    """Set the global thread ID for conversation memory."""
    global _thread_id
    _thread_id = tid
