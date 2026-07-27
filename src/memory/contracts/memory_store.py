"""Abstract Base Classes for Memory Management (ISP / LSP)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MemoryRecord(BaseModel):
    """Normalized memory entry."""
    record_id: str
    session_id: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None


class BaseMemoryStore(ABC):
    """Abstract Interface for Session & Ephemeral Memory Management."""

    @abstractmethod
    async def add(self, session_id: str, message_type: str, content: str) -> None:
        """Stores a interaction record into session memory."""
        pass

    @abstractmethod
    async def get_recent_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent conversation history."""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        """Clears memory for a specific session."""
        pass


class VectorMemoryContract(ABC):
    """Abstract Interface for Vector Retrieval Augmented Generation (RAG)."""

    @abstractmethod
    async def upsert(self, records: List[MemoryRecord]) -> bool:
        """Inserts or updates vector embeddings in long-term memory."""
        pass

    @abstractmethod
    async def search_similar(self, query_vector: List[float], top_k: int = 5) -> List[MemoryRecord]:
        """Queries semantically similar memory records."""
        pass
