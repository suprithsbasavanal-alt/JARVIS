"""Core types and data models for JARVIS."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class EnvironmentType(str, Enum):
    """Execution environment mode."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ExecutionContext(str, Enum):
    """Context category for conversational persona and security."""
    PRIVATE = "private"       # Address as "Suprith"
    FORMAL = "formal"         # Address as "Sir"
    PUBLIC = "public"         # Address as "Sir"


class ActionCategory(str, Enum):
    """Taxonomy of tool and action risks."""
    SAFE = "SAFE"                     # Read-only, no side effects
    REVERSIBLE = "REVERSIBLE"         # Easily undone local modifications
    SENSITIVE = "SENSITIVE"           # External communication, data sharing
    DESTRUCTIVE = "DESTRUCTIVE"       # File deletion, database drops
    IRREVERSIBLE = "IRREVERSIBLE"     # Purchasing, permanently deleting accounts


class BaseDomainEvent(BaseModel):
    """Base event model for the internal event bus."""
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
