"""Base domain types and enums for Jarvis."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ExecutionStatus(str, Enum):
    """Execution status for agent tasks and tool calls."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class DomainEntity:
    """Base class for all domain entities in Jarvis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
