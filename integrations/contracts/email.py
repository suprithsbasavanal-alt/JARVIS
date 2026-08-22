"""Abstract Email Integration Contract (Gmail / IMAP)."""

from abc import ABC, abstractmethod
from core.compat import BaseModel, Field
from integrations.base import BaseIntegration


class EmailMessage(BaseModel):
    """Normalized email message structure."""
    message_id: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    received_at: str


class EmailDraft(BaseModel):
    """Email composition payload."""
    recipient: str
    subject: str
    body_text: str
    attachments: list[str] = Field(default_factory=list)


class EmailContract(BaseIntegration, ABC):
    """Abstract contract for email services."""

    @abstractmethod
    async def list_unread_messages(self, limit: int = 10) -> list[EmailMessage]:
        """Fetch unread messages (NORMAL tier)."""
        pass

    @abstractmethod
    async def create_draft(self, draft: EmailDraft) -> str:
        """Create draft email (NORMAL tier). Returns draft_id."""
        pass

    @abstractmethod
    async def send_email(self, draft_id: str, approval_token: str) -> bool:
        """Dispatch email (SENSITIVE tier - requires approval token)."""
        pass
