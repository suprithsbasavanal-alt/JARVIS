"""Conversation Session Lifecycle Manager."""

from uuid import UUID
from conversation.history import DialogueTurn
from conversation.personality import PersonaGovernor
from core.context import SessionContext
from model_routing.schemas import ChatMessage, MessageRole


class ConversationSession:
    """Manages active dialogue state, persona prompts, and history turns."""

    def __init__(self, context: SessionContext | None = None) -> None:
        self.context = context or SessionContext()
        self.turns: list[DialogueTurn] = []

    def get_system_message(self) -> ChatMessage:
        """Construct active system prompt message."""
        content = PersonaGovernor.construct_system_prompt(self.context)
        return ChatMessage(role=MessageRole.SYSTEM, content=content)

    def record_turn(self, user_query: str, assistant_reply: str, tools: list[str] | None = None) -> DialogueTurn:
        """Record completed conversational turn."""
        self.context.touch()
        turn = DialogueTurn(
            user_query=user_query,
            assistant_reply=assistant_reply,
            tools_invoked=tools or [],
        )
        self.turns.append(turn)
        return turn

    def get_context_messages(self, max_turns: int = 10) -> list[ChatMessage]:
        """Assemble full message list for model request including system prompt."""
        messages: list[ChatMessage] = [self.get_system_message()]
        for turn in self.turns[-max_turns:]:
            messages.extend(turn.to_chat_messages())
        return messages


class SessionManager:
    """Registry and controller for multiple conversation sessions."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, ConversationSession] = {}

    def create_session(self, context: SessionContext | None = None) -> ConversationSession:
        """Initialize a new conversation session."""
        session = ConversationSession(context=context)
        self._sessions[session.context.session_id] = session
        return session

    def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve existing session."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: UUID) -> bool:
        """Terminate a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
