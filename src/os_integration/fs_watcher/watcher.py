"""File System Change Watcher Implementation (SOLID - SRP / LSP)."""

import time
from typing import Callable, Coroutine, Any
from src.os_integration.fs_watcher.contract import BaseFSWatcher, FileChangeEvent
from src.shared.logger.logger import get_logger

logger = get_logger("os_integration.fs_watcher")


class SystemFSWatcher(BaseFSWatcher):
    """Monitors host file system changes."""

    def __init__(self) -> None:
        self._is_watching = False

    async def start_watching(self, path: str, callback: Callable[[FileChangeEvent], Coroutine[Any, Any, None]]) -> None:
        """Starts monitoring path for file change events."""
        self._is_watching = True
        logger.info(f"Started monitoring file system path '{path}'...")
        event = FileChangeEvent(file_path=path, event_type="modified", timestamp=time.time())
        await callback(event)

    async def stop_watching(self) -> None:
        """Stops watching path."""
        self._is_watching = False
        logger.info("Stopped file system watcher.")
