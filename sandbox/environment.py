"""Hermetic Sandbox Environment Controller."""

from pathlib import Path
from sandbox.mock_fs import MockFilesystem
from sandbox.mock_services import MockCalendarService, MockEmailService, MockMessagingService


class SandboxEnvironment:
    """Encapsulates all simulated tools, virtual filesystems, and synthetic data for safe development."""

    def __init__(self, sandbox_root: Path | None = None) -> None:
        self.fs = MockFilesystem(sandbox_root)
        self.email_service = MockEmailService()
        self.calendar_service = MockCalendarService()
        self.messaging_service = MockMessagingService()

    def reset(self) -> None:
        """Reset the sandbox state."""
        self.email_service.sent_emails.clear()
        self.calendar_service.created_events.clear()
        self.messaging_service.outbound_queue.clear()
