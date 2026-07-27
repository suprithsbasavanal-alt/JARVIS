"""Abstract Base Classes for OS File System Watcher (DIP)."""

from abc import ABC, abstractmethod
from typing import Callable, Coroutine, Any
from pydantic import BaseModel


class FileChangeEvent(BaseModel):
    """File system change event."""
    file_path: str
    event_type: str  # created, modified, deleted
    timestamp: float


class BaseFSWatcher(ABC):
    """Abstract Interface for File System Monitoring."""

    @abstractmethod
    async def start_watching(self, path: str, callback: Callable[[FileChangeEvent], Coroutine[Any, Any, None]]) -> None:
        """Starts monitoring target path for file events."""
        pass

    @abstractmethod
    async def stop_watching(self) -> None:
        """Stops watching target directory."""
        pass
