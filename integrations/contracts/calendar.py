"""Abstract Calendar Integration Contract (Google / Apple Calendar)."""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from integrations.base import BaseIntegration


class CalendarEvent(BaseModel):
    """Normalized calendar event representation."""
    event_id: str
    title: str
    start_time_iso: str
    end_time_iso: str
    attendees: list[str] = Field(default_factory=list)
    location: str | None = None
    description: str | None = None


class CalendarContract(BaseIntegration, ABC):
    """Abstract contract for calendar services."""

    @abstractmethod
    async def list_upcoming_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        """List upcoming events (NORMAL tier)."""
        pass

    @abstractmethod
    async def create_event(self, event: CalendarEvent, approval_token: str) -> str:
        """Create new calendar event (SENSITIVE tier - requires approval token)."""
        pass

    @abstractmethod
    async def delete_event(self, event_id: str, approval_token: str) -> bool:
        """Delete calendar event (SENSITIVE / DESTRUCTIVE tier - requires approval token)."""
        pass
