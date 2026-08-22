"""Integrations Package."""

from integrations.base import BaseIntegration
from integrations.contracts import (
    CalendarContract,
    CalendarEvent,
    ChatMessageItem,
    EmailContract,
    EmailDraft,
    EmailMessage,
    MessagingContract,
    OutboundChatMessage,
    SystemContract,
)

__all__ = [
    "BaseIntegration",
    "CalendarContract",
    "CalendarEvent",
    "ChatMessageItem",
    "EmailContract",
    "EmailDraft",
    "EmailMessage",
    "MessagingContract",
    "OutboundChatMessage",
    "SystemContract",
]
