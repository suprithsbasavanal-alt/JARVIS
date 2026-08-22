"""Hermetic Mock External Services Backed by Static Fixtures."""

import json
from pathlib import Path
from uuid import uuid4
from integrations.contracts.calendar import CalendarContract, CalendarEvent
from integrations.contracts.email import EmailContract, EmailDraft, EmailMessage
from integrations.contracts.messaging import (
    ChatMessageItem,
    MessagingContract,
    OutboundChatMessage,
)


class MockEmailService(EmailContract):
    """Mock Email Service backed by sandbox/fixtures/mock_emails.json."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        super().__init__(service_name="mock_email", is_mock=True)
        self.fixture_path = fixture_path or Path("sandbox/fixtures/mock_emails.json")
        self.sent_emails: list[dict[str, str]] = []

    async def is_available(self) -> bool:
        return True

    async def list_unread_messages(self, limit: int = 10) -> list[EmailMessage]:
        if not self.fixture_path.exists():
            return []
        with open(self.fixture_path, encoding="utf-8") as f:
            data = json.load(f)
            return [EmailMessage(**item) for item in data[:limit]]

    async def create_draft(self, draft: EmailDraft) -> str:
        return f"draft-mock-{uuid4()}"

    async def send_email(self, draft_id: str, approval_token: str) -> bool:
        self.sent_emails.append({"draft_id": draft_id, "token": approval_token})
        return True


class MockCalendarService(CalendarContract):
    """Mock Calendar Service backed by sandbox/fixtures/mock_events.json."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        super().__init__(service_name="mock_calendar", is_mock=True)
        self.fixture_path = fixture_path or Path("sandbox/fixtures/mock_events.json")
        self.created_events: list[CalendarEvent] = []

    async def is_available(self) -> bool:
        return True

    async def list_upcoming_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        if not self.fixture_path.exists():
            return []
        with open(self.fixture_path, encoding="utf-8") as f:
            data = json.load(f)
            return [CalendarEvent(**item) for item in data]

    # Alias for convenience
    list_events = list_upcoming_events

    async def create_event(self, event: CalendarEvent, approval_token: str) -> str:
        self.created_events.append(event)
        return event.event_id

    async def delete_event(self, event_id: str, approval_token: str) -> bool:
        return True


class MockMessagingService(MessagingContract):
    """Mock Messaging Service backed by sandbox/fixtures/mock_messages.json."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        super().__init__(service_name="mock_messaging", is_mock=True)
        self.fixture_path = fixture_path or Path("sandbox/fixtures/mock_messages.json")
        self.outbound_queue: list[OutboundChatMessage] = []

    async def is_available(self) -> bool:
        return True

    async def list_recent_messages(self, platform: str, limit: int = 10) -> list[ChatMessageItem]:
        if not self.fixture_path.exists():
            return []
        with open(self.fixture_path, encoding="utf-8") as f:
            data = json.load(f)
            filtered = [item for item in data if item["platform"] == platform]
            return [ChatMessageItem(**item) for item in filtered[:limit]]

    async def send_message(self, message: OutboundChatMessage, approval_token: str) -> bool:
        self.outbound_queue.append(message)
        return True
