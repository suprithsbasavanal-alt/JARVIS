"""Memory Indexing and Future Vector Search Interfaces."""

from abc import ABC, abstractmethod
from collections import defaultdict
from uuid import UUID
from memory.long_term import MemoryRecord, MemoryType, SensitivityLevel


class MemoryIndex(ABC):
    """Abstract interface for memory search indexing."""

    @abstractmethod
    def index_record(self, record: MemoryRecord) -> None:
        """Add or update record in index."""
        pass

    @abstractmethod
    def remove_record(self, memory_id: UUID) -> None:
        """Remove record from index."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        category: MemoryType | None = None,
        max_sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """Query indexed memories."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Purge index."""
        pass


class KeywordMemoryIndex(MemoryIndex):
    """In-memory inverted keyword index for sub-millisecond retrieval in Phase 2."""

    def __init__(self) -> None:
        self._records: dict[UUID, MemoryRecord] = {}
        self._inverted_index: dict[str, set[UUID]] = defaultdict(set)

    def _tokenize(self, text: str) -> list[str]:
        """Extract lowercase word tokens."""
        clean = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return [tok for tok in clean.split() if len(tok) > 1]

    def index_record(self, record: MemoryRecord) -> None:
        """Index a memory record."""
        self.remove_record(record.memory_id)
        if not record.is_active:
            return

        self._records[record.memory_id] = record
        tokens = set(self._tokenize(record.content))
        for tag in record.tags:
            tokens.update(self._tokenize(tag))

        for token in tokens:
            self._inverted_index[token].add(record.memory_id)

    def remove_record(self, memory_id: UUID) -> None:
        """Remove record from inverted index and registry."""
        if memory_id in self._records:
            del self._records[memory_id]
            for token, mid_set in list(self._inverted_index.items()):
                mid_set.discard(memory_id)
                if not mid_set:
                    del self._inverted_index[token]

    def search(
        self,
        query: str,
        category: MemoryType | None = None,
        max_sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """Retrieve memories matching query tokens with scoring."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: dict[UUID, int] = defaultdict(int)
        for tok in query_tokens:
            for mid in self._inverted_index.get(tok, set()):
                scores[mid] += 1

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        results: list[MemoryRecord] = []

        for mid, _ in ranked:
            rec = self._records.get(mid)
            if not rec or not rec.is_active:
                continue
            if category and rec.category != category:
                continue
            if rec.sensitivity == SensitivityLevel.SENSITIVE and max_sensitivity != SensitivityLevel.SENSITIVE:
                continue
            results.append(rec)
            if len(results) >= limit:
                break

        return results

    def clear(self) -> None:
        """Clear all indexed records."""
        self._records.clear()
        self._inverted_index.clear()


# =====================================================================
# Future Vector Search Interface Stubs (Phase 4 / Phase 11)
# =====================================================================

class EmbeddingProvider(ABC):
    """Abstract interface for dense vector text embeddings."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector."""
        pass


class VectorIndex(ABC):
    """Abstract interface for vector similarity search."""

    @abstractmethod
    async def insert_vector(self, vector_id: str, vector: list[float], metadata: dict[str, str]) -> None:
        pass

    @abstractmethod
    async def search_vector(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, str]]:
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for zero-overhead Phase 2 execution."""

    async def embed_text(self, text: str) -> list[float]:
        # Return deterministic synthetic 8-dimensional unit vector
        return [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


class MockVectorIndex(VectorIndex):
    """Mock vector index for zero-overhead Phase 2 execution."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}

    async def insert_vector(self, vector_id: str, vector: list[float], metadata: dict[str, str]) -> None:
        self._vectors[vector_id] = vector

    async def search_vector(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, str]]:
        return []
