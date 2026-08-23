"""Memory Record Data Models, Enums, and Metadata."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from core.compat import BaseModel, Field


class MemoryType(str, Enum):
    """Classification of memory categories."""
    WORKING = "WORKING"         # Ephemeral turn / session context
    EPISODIC = "EPISODIC"       # Explicitly permitted interaction summaries / events
    SEMANTIC = "SEMANTIC"       # Stable user-approved facts / preferences
    SENSITIVE = "SENSITIVE"     # Highly sensitive data requiring elevated protection
    USER_PREFERENCE = "USER_PREFERENCE"  # User preference memory item


# Alias for backward compatibility
MemoryCategory = MemoryType


class ConsentStatus(str, Enum):
    """Consent provenance tracking."""
    EXPLICIT_APPROVED = "EXPLICIT_APPROVED"   # Created by direct user instruction
    MODEL_SUGGESTED = "MODEL_SUGGESTED"       # Proposed by assistant, awaiting user confirmation
    TEMPORARY = "TEMPORARY"                   # Session-bound, unpersisted


class SensitivityLevel(str, Enum):
    """Sensitivity level for access control."""
    NORMAL = "NORMAL"
    SENSITIVE = "SENSITIVE"


class RetentionPolicy(str, Enum):
    """Retention lifecycle policies."""
    PERMANENT = "PERMANENT"
    EXPIRE_AFTER_DAYS = "EXPIRE_AFTER_DAYS"
    SESSION_ONLY = "SESSION_ONLY"


class MemoryRecord(BaseModel):
    """Persistent unit of knowledge with structured metadata and audit provenance."""
    memory_id: UUID = Field(default_factory=uuid4)
    category: MemoryType = MemoryType.SEMANTIC
    content: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_session_id: str = "default_session"
    consent_status: ConsentStatus = ConsentStatus.EXPLICIT_APPROVED
    sensitivity: SensitivityLevel = SensitivityLevel.NORMAL
    encryption_status: bool = False
    retention_policy: RetentionPolicy = RetentionPolicy.PERMANENT
    retention_days: int = 0
    version: int = 1
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)

    def mark_updated(self, new_content: str) -> "MemoryRecord":
        """Produce a new active version of this memory record."""
        return self.model_copy(
            update={
                "content": new_content,
                "version": self.version + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
