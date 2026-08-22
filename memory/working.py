"""Working Memory (In-RAM Ephemeral Context)."""

from model_routing.schemas import ChatMessage


class WorkingMemory:
    """Ephemeral sliding-window dialogue buffer for active sessions."""

    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self._messages: list[ChatMessage] = []

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the working memory, maintaining sliding window."""
        self._messages.append(message)
        if len(self._messages) > self.max_items:
            # Maintain system messages at index 0 if present, slide user/assistant messages
            if self._messages[0].role.value == "system":
                self._messages = [self._messages[0]] + self._messages[-(self.max_items - 1):]
            else:
                self._messages = self._messages[-self.max_items:]

    def get_messages(self) -> list[ChatMessage]:
        """Retrieve all active messages."""
        return list(self._messages)

    def clear(self) -> None:
        """Flush in-memory working buffer."""
        self._messages.clear()
