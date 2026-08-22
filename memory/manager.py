"""Unified Memory Subsystem Manager."""

from uuid import UUID
from memory.long_term import LongTermMemoryItem, MemoryCategory
from memory.store import BaseMemoryStore, MockMemoryStore
from memory.working import WorkingMemory
from model_routing.schemas import ChatMessage


class MemoryManager:
    """Coordinates working memory, encrypted persistent storage, and privacy controls."""

    def __init__(self, store: BaseMemoryStore | None = None, max_working_items: int = 20) -> None:
        self.working_memory = WorkingMemory(max_items=max_working_items)
        self.store = store or MockMemoryStore()

    def add_working_message(self, message: ChatMessage) -> None:
        """Append to active conversation window."""
        self.working_memory.add_message(message)

    def get_working_messages(self) -> list[ChatMessage]:
        """Retrieve recent conversation turns."""
        return self.working_memory.get_messages()

    def clear_working_memory(self) -> None:
        """Purge current session buffer."""
        self.working_memory.clear()

    async def remember(
        self,
        content: str,
        category: MemoryCategory,
        session_id: str,
        confidence: float = 1.0,
        tags: list[str] | None = None,
    ) -> LongTermMemoryItem:
        """Store a user-approved persistent memory item."""
        item = LongTermMemoryItem(
            content=content,
            category=category,
            source_session_id=session_id,
            confidence_score=confidence,
            tags=tags or [],
            is_user_approved=True,
        )
        await self.store.save_item(item)
        return item

    async def recall(self, query: str, category: MemoryCategory | None = None, limit: int = 5) -> list[LongTermMemoryItem]:
        """Retrieve relevant memories matching query."""
        return await self.store.search_items(query, category=category, limit=limit)

    async def forget_item(self, memory_id: UUID) -> bool:
        """Delete specific memory item (Right to be Forgotten)."""
        return await self.store.delete_item(memory_id)

    async def wipe_topic(self, topic: str) -> int:
        """Purge all memory items related to a topic."""
        return await self.store.delete_by_topic(topic)

    async def factory_reset_memory(self) -> None:
        """Wipe all working and long-term memory."""
        self.working_memory.clear()
        await self.store.clear_all()
