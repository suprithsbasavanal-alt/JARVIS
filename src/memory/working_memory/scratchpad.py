"""Working Memory Scratchpad for Active Task State Management."""

from typing import Any, Dict, Optional
from src.shared.logger.logger import get_logger

logger = get_logger("memory.working_memory")


class WorkingMemoryScratchpad:
    """Ephemeral Key-Value Scratchpad during active task execution."""

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Stores a temporary state variable into scratchpad."""
        self._state[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieves temporary state variable."""
        return self._state.get(key, default)

    def has(self, key: str) -> bool:
        """Checks if key exists in scratchpad state."""
        return key in self._state

    def clear(self) -> None:
        """Wipes active scratchpad state."""
        self._state.clear()
        logger.debug("Working memory scratchpad cleared.")
