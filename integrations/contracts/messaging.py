"""Abstract Messaging Contract (WhatsApp / Telegram / SMS)."""

from abc import ABC, abstractmethod
from typing import Literal
from pydantic import BaseModel
from integrations.base import BaseIntegration


class ChatMessageItem(BaseModel):
    """Normalized chat message structure."""
    message_id: str
    platform: Literal["whatsapp", "telegram", "sms"]
    sender: str
    recipient: str
    text_content: str
    timestamp_iso: str


class OutboundChatMessage(BaseModel):
    """Payload for sending chat message."""
    platform: Literal["whatsapp", "telegram", "sms"]
    recipient: str
    text_content: str


class MessagingContract(BaseIntegration, ABC):
    """Abstract contract for instant messaging platforms."""

    @abstractmethod
    async def list_recent_messages(self, platform: str, limit: int = 10) -> list[ChatMessageItem]:
        """Fetch recent message snippets (NORMAL tier)."""
        pass

    @abstractmethod
    async def send_message(self, message: OutboundChatMessage, approval_token: str) -> bool:
        """Send outbound message (SENSITIVE tier - requires approval token)."""
        pass
