"""Long-Term Vector Semantic Memory Store (RAG / LSP)."""

import math
from typing import List
from src.memory.contracts.memory_store import VectorMemoryContract, MemoryRecord
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("memory.long_term")


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two numeric vector arrays."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class VectorMemoryStore(VectorMemoryContract):
    """Vector Semantic Memory Index for RAG retrieval."""

    def __init__(self, collection_name: str = None) -> None:
        self.collection_name = collection_name or settings.database.vector_collection_name
        self._records: List[MemoryRecord] = []

    async def upsert(self, records: List[MemoryRecord]) -> bool:
        """Upserts records into vector index."""
        for rec in records:
            # Remove existing record with same ID if present
            self._records = [r for r in self._records if r.record_id != rec.record_id]
            self._records.append(rec)
        logger.info(f"Upserted {len(records)} records into vector index '{self.collection_name}'. Total: {len(self._records)}")
        return True

    async def search_similar(self, query_vector: List[float], top_k: int = 5) -> List[MemoryRecord]:
        """Performs cosine similarity search against stored vector embeddings."""
        if not query_vector:
            return []

        scored_records = []
        for record in self._records:
            if record.embedding:
                score = _cosine_similarity(query_vector, record.embedding)
                scored_records.append((score, record))

        # Sort descending by similarity score
        scored_records.sort(key=lambda x: x[0], reverse=True)
        results = [rec for _, rec in scored_records[:top_k]]
        logger.debug(f"Retrieved top {len(results)} semantically similar vector records.")
        return results
