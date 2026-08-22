"""Dialogue Turn Record and Structured History Container."""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from model_routing.schemas import ChatMessage, MessageRole


class DialogueTurn(BaseModel):
    """Encapsulates a single user-assistant exchange turn."""
    turn_id: UUID = Field(default_factory=uuid4)
    user_query: str
    assistant_reply: str
    tools_invoked: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_chat_messages(self) -> list[ChatMessage]:
        """Convert turn to pair of chat messages."""
        return [
            ChatMessage(role=MessageRole.USER, content=self.user_query),
            ChatMessage(role=MessageRole.ASSISTANT, content=self.assistant_reply),
        ]
