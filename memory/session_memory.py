"""Session memory helper — provides context summaries and error extraction.

With LangChain 1.x, conversation memory is managed by the checkpointer
(SqliteSaver). This module provides utilities to inspect and export that state.
"""

import json
from pathlib import Path
from typing import Any


class SessionMemory:
    """Helper for inspecting agent conversation state.

    The primary memory mechanism is SqliteSaver (checkpointer), which
    persists all messages per thread_id automatically. This class
    provides convenience methods for context summaries, error extraction,
    and JSON export/import of conversation state.
    """

    def __init__(self, filepath: str = "./session_memory.json"):
        self.filepath = Path(filepath)
        self._messages: list[dict[str, str]] = []
        self._load()

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages

    def add_user_message(self, message: str) -> None:
        self._messages.append({"type": "human", "content": message})

    def add_ai_message(self, message: str) -> None:
        self._messages.append({"type": "ai", "content": message})

    def get_context_summary(self, last_n: int = 4) -> str:
        """Get the last N exchanges as a plain-text summary for prompt injection."""
        if not self._messages:
            return "（无历史对话）"

        recent = self._messages[-last_n * 2:]
        lines = []
        for msg in recent:
            role = "用户" if msg["type"] == "human" else "助手"
            content = msg["content"][:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def extract_last_error(self) -> str | None:
        """Extract the last error from conversation for auto-fix context."""
        for msg in reversed(self._messages):
            if msg["type"] == "ai" and "❌" in msg["content"]:
                return msg["content"]
        return None

    def save(self) -> None:
        """Export messages to a JSON file for backup/inspection."""
        data = {"messages": self._messages}
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load(self) -> None:
        """Load messages from JSON backup if it exists."""
        if not self.filepath.exists():
            return
        try:
            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            self._messages = data.get("messages", [])
        except (json.JSONDecodeError, KeyError):
            pass

    def clear(self) -> None:
        """Clear all messages and delete the backup file."""
        self._messages.clear()
        if self.filepath.exists():
            self.filepath.unlink()

    def __len__(self) -> int:
        return len(self._messages)
