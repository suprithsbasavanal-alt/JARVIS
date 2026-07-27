"""Short-Term Ephemeral Session Memory Store (SOLID - SRP / LSP)."""

from typing import Any, Dict, List
from src.memory.contracts.memory_store import BaseMemoryStore
from src.shared.logger.logger import get_logger

logger = get_logger("memory.short_term")


class ShortTermSessionMemory(BaseMemoryStore):
    """In-memory sliding window conversation history storage per session."""

    def __init__(self, max_history_per_session: int = 50) -> None:
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history = max_history_per_session

    async def add(self, session_id: str, message_type: str, content: str) -> None:
        """Stores interaction record into target session history buffer."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        record = {
            "type": message_type,
            "content": content,
        }
        self._sessions[session_id].append(record)

        # Enforce sliding window capacity limit
        if len(self._sessions[session_id]) > self.max_history:
            self._sessions[session_id] = self._sessions[session_id][-self.max_history:]

        logger.debug(f"Added '{message_type}' memory record to session '{session_id}'. Total: {len(self._sessions[session_id])}")

    async def get_recent_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent conversation history for session."""
        history = self._sessions.get(session_id, [])
        return history[-limit:]

    async def clear_session(self, session_id: str) -> None:
        """Clears memory for specific session ID."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared session memory for '{session_id}'.")
