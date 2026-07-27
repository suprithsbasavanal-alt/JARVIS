"""Abstract Repository Contracts (Repository Pattern / DIP)."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar
from src.shared.types.base import DomainEntity

T = TypeVar("T", bound=DomainEntity)


class BaseRepository(ABC, Generic[T]):
    """Generic Repository Interface for Domain Entities."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Fetches single entity by ID."""
        pass

    @abstractmethod
    async def list_all(self) -> List[T]:
        """Lists all entities."""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persists or updates an entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Deletes entity by ID."""
        pass
