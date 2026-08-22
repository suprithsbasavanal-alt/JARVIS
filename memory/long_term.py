"""Long-Term Memory Data Models and Categorization."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    """Classification for long-term stored facts."""
    USER_PREFERENCE = "preference"
    PROJECT_CONTEXT = "project"
    TASK_STATE = "task"
    FACTUAL_KNOWLEDGE = "fact"


class LongTermMemoryItem(BaseModel):
    """Persistent unit of episodic or semantic knowledge."""
    memory_id: UUID = Field(default_factory=uuid4)
    content: str
    category: MemoryCategory
    source_session_id: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_user_approved: bool = True
    tags: list[str] = Field(default_factory=list)
