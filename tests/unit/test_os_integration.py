"""Unit Test Suite for OS Integration Component."""

import pytest
from src.os_integration import (
    SystemFSWatcher,
    SystemProcessRunner,
    NativeNotificationService,
    FileChangeEvent,
)


@pytest.mark.asyncio
async def test_system_fs_watcher():
    """Verifies SystemFSWatcher callback triggers."""
    watcher = SystemFSWatcher()
    events_received = []

    async def on_event(event: FileChangeEvent):
        events_received.append(event)

    await watcher.start_watching(".", on_event)
    assert len(events_received) == 1
    assert events_received[0].event_type == "modified"

    await watcher.stop_watching()
    assert watcher._is_watching is False


@pytest.mark.asyncio
async def test_system_process_runner():
    """Verifies SystemProcessRunner shell execution."""
    runner = SystemProcessRunner()
    res = await runner.run_command("echo 'Jarvis Test Process'")
    assert res["success"] is True
    assert res["stdout"] == "Jarvis Test Process"


def test_native_notification_service():
    """Verifies NativeNotificationService notification dispatch."""
    service = NativeNotificationService()
    sent = service.notify("Test Notification", "Jarvis process complete.")
    assert sent is True
