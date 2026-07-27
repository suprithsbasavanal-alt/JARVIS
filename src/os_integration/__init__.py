"""OS Integration Package."""

from .fs_watcher.contract import BaseFSWatcher, FileChangeEvent
from .fs_watcher.watcher import SystemFSWatcher
from .process_runner.runner import SystemProcessRunner
from .native_hooks.notifications import NativeNotificationService

__all__ = [
    "BaseFSWatcher",
    "FileChangeEvent",
    "SystemFSWatcher",
    "SystemProcessRunner",
    "NativeNotificationService",
]
