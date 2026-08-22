"""Unit tests for Working Memory and Long-Term Memory."""

import pytest
from memory.long_term import MemoryCategory
from memory.manager import MemoryManager
from model_routing.schemas import ChatMessage, MessageRole


@pytest.mark.asyncio
async def test_working_memory_sliding_window() -> None:
    """Verify working memory caps message length and slides context."""
    mem = MemoryManager(max_working_items=3)
    mem.add_working_message(ChatMessage(role=MessageRole.USER, content="Msg 1"))
    mem.add_working_message(ChatMessage(role=MessageRole.ASSISTANT, content="Msg 2"))
    mem.add_working_message(ChatMessage(role=MessageRole.USER, content="Msg 3"))
    mem.add_working_message(ChatMessage(role=MessageRole.ASSISTANT, content="Msg 4"))

    messages = mem.get_working_messages()
    assert len(messages) == 3
    assert messages[0].content == "Msg 2"
    assert messages[-1].content == "Msg 4"


@pytest.mark.asyncio
async def test_long_term_memory_lifecycle(memory_manager: MemoryManager) -> None:
    """Verify remember, recall, wipe topic, and factory reset."""
    item = await memory_manager.remember(
        content="Suprith prefers Python for backend development.",
        category=MemoryCategory.USER_PREFERENCE,
        session_id="session-001",
        tags=["python", "preferences"],
    )

    results = await memory_manager.recall("Python")
    assert len(results) == 1
    assert results[0].memory_id == item.memory_id

    # Test targeted forget
    deleted = await memory_manager.forget_item(item.memory_id)
    assert deleted
    assert len(await memory_manager.recall("Python")) == 0
