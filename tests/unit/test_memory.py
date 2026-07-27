"""Unit Test Suite for Memory Component."""

import pytest
from src.memory import (
    ShortTermSessionMemory,
    VectorMemoryStore,
    WorkingMemoryScratchpad,
    MemoryRecord,
)


@pytest.mark.asyncio
async def test_short_term_session_memory():
    """Verifies ShortTermSessionMemory sliding window and session isolation."""
    mem = ShortTermSessionMemory(max_history_per_session=3)

    await mem.add("sess_1", "user", "Hello")
    await mem.add("sess_1", "assistant", "Hi there")
    await mem.add("sess_1", "user", "How are you?")
    await mem.add("sess_1", "assistant", "I am operational.")

    history = await mem.get_recent_history("sess_1", limit=10)
    assert len(history) == 3  # Maximum sliding history enforced
    assert history[0]["content"] == "Hi there"
    assert history[-1]["content"] == "I am operational."

    await mem.clear_session("sess_1")
    cleared_history = await mem.get_recent_history("sess_1")
    assert len(cleared_history) == 0


@pytest.mark.asyncio
async def test_vector_memory_store_cosine_search():
    """Verifies VectorMemoryStore semantic similarity search ranking."""
    store = VectorMemoryStore(collection_name="test_collection")

    rec1 = MemoryRecord(
        record_id="rec_1",
        session_id="s1",
        content="Python Clean Architecture",
        embedding=[1.0, 0.0, 0.0]
    )
    rec2 = MemoryRecord(
        record_id="rec_2",
        session_id="s1",
        content="Docker Containerization",
        embedding=[0.0, 1.0, 0.0]
    )
    rec3 = MemoryRecord(
        record_id="rec_3",
        session_id="s1",
        content="Python SOLID Principles",
        embedding=[0.9, 0.1, 0.0]
    )

    await store.upsert([rec1, rec2, rec3])

    # Search for query vector close to Python [1.0, 0.0, 0.0]
    query_vector = [0.95, 0.05, 0.0]
    results = await store.search_similar(query_vector, top_k=2)

    assert len(results) == 2
    assert results[0].record_id == "rec_1"
    assert results[1].record_id == "rec_3"


def test_working_memory_scratchpad():
    """Verifies WorkingMemoryScratchpad key-value operations."""
    pad = WorkingMemoryScratchpad()
    pad.set("active_task", "indexing")
    assert pad.has("active_task") is True
    assert pad.get("active_task") == "indexing"
    assert pad.get("missing_key", "default_val") == "default_val"

    pad.clear()
    assert pad.has("active_task") is False
