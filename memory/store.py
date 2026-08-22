"""Abstract Memory Storage Engine and Hermetic Mock Implementation."""

from abc import ABC, abstractmethod
from uuid import UUID
from memory.long_term import LongTermMemoryItem, MemoryCategory


class BaseMemoryStore(ABC):
    """Abstract interface for encrypted persistent memory storage."""

    @abstractmethod
    async def save_item(self, item: LongTermMemoryItem) -> None:
        """Persist a memory item."""
        pass

    @abstractmethod
    async def get_item(self, memory_id: UUID) -> LongTermMemoryItem | None:
        """Fetch memory item by ID."""
        pass

    @abstractmethod
    async def search_items(self, query: str, category: MemoryCategory | None = None, limit: int = 5) -> list[LongTermMemoryItem]:
        """Search memory by semantic or keyword query."""
        pass

    @abstractmethod
    async def delete_item(self, memory_id: UUID) -> bool:
        """Delete specific memory item."""
        pass

    @abstractmethod
    async def delete_by_topic(self, topic: str) -> int:
        """Purge all memory items related to a topic."""
        pass

    @abstractmethod
    async def clear_all(self) -> None:
        """Full factory reset of all stored memories."""
        pass


class MockMemoryStore(BaseMemoryStore):
    """Hermetic in-memory store for Phase 0 safe development."""

    def __init__(self) -> None:
        self._items: dict[UUID, LongTermMemoryItem] = {}

    async def save_item(self, item: LongTermMemoryItem) -> None:
        self._items[item.memory_id] = item

    async def get_item(self, memory_id: UUID) -> LongTermMemoryItem | None:
        return self._items.get(memory_id)

    async def search_items(self, query: str, category: MemoryCategory | None = None, limit: int = 5) -> list[LongTermMemoryItem]:
        results: list[LongTermMemoryItem] = []
        q_lower = query.lower()
        for item in self._items.values():
            if category and item.category != category:
                continue
            if q_lower in item.content.lower() or any(q_lower in tag.lower() for tag in item.tags):
                results.append(item)
            if len(results) >= limit:
                break
        return results

    async def delete_item(self, memory_id: UUID) -> bool:
        if memory_id in self._items:
            del self._items[memory_id]
            return True
        return False

    async def delete_by_topic(self, topic: str) -> int:
        to_delete = [
            mid for mid, item in self._items.items()
            if topic.lower() in item.content.lower() or any(topic.lower() in t.lower() for t in item.tags)
        ]
        for mid in to_delete:
            del self._items[mid]
        return len(to_delete)

    async def clear_all(self) -> None:
        self._items.clear()
