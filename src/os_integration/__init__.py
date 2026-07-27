"""OS Integration Package."""

from .fs_watcher.contract import BaseFSWatcher, FileChangeEvent

__all__ = [
    "BaseFSWatcher",
    "FileChangeEvent",
]
