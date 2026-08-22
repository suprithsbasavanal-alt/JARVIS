"""Typed Tool Contract and Capability Definitions for Phase 3."""

from abc import ABC, abstractmethod
from enum import Enum
import time
from typing import Any
from config.schema import PermissionLevel
from core.compat import BaseModel, Field
from core.context import SessionContext
from core.types import ActionCategory


class ToolCapability(str, Enum):
    """Granular capability categories for tools."""
    READ_ONLY = "READ_ONLY"
    COMPUTATION = "COMPUTATION"
    MEMORY = "MEMORY"
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    COMMUNICATION = "COMMUNICATION"
    CALENDAR = "CALENDAR"
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    NETWORK = "NETWORK"
    RESEARCH = "RESEARCH"
    DESTRUCTIVE = "DESTRUCTIVE"
    FINANCIAL = "FINANCIAL"


class RiskLevel(str, Enum):
    """Risk classification for tool actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SideEffectLevel(str, Enum):
    """Side effect impact level."""
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    IRREVERSIBLE = "IRREVERSIBLE"


class ToolDefinition(BaseModel):
    """Strongly typed tool specification and capability contract."""
    tool_id: str
    name: str
    description: str
    version: str = "1.0.0"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    capability: ToolCapability = ToolCapability.READ_ONLY
    permission_tier: PermissionLevel = PermissionLevel.NORMAL
    risk_level: RiskLevel = RiskLevel.LOW
    allowed_environment: str = "SANDBOX_ONLY"
    requires_confirmation: bool = False
    timeout_seconds: float = 5.0
    max_output_size_bytes: int = 65536  # 64KB
    side_effect_level: SideEffectLevel = SideEffectLevel.NONE

    # Backward compatibility properties
    @property
    def action_category(self) -> ActionCategory:
        """Map capability & risk to ActionCategory for backward compatibility."""
        if self.requires_confirmation or self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return ActionCategory.SENSITIVE
        if self.side_effect_level == SideEffectLevel.WRITE:
            return ActionCategory.REVERSIBLE
        return ActionCategory.SAFE

    @property
    def required_permission_level(self) -> PermissionLevel:
        return self.permission_tier

    @property
    def parameter_schema(self) -> dict[str, Any]:
        return self.input_schema

    @property
    def is_sandboxed_only(self) -> bool:
        return self.allowed_environment in ("SANDBOX_ONLY", "PROCESS_ISOLATED")


# Alias ToolMetadata to ToolDefinition for backward compatibility
ToolMetadata = ToolDefinition


class ToolResult(BaseModel):
    """Structured result returned by tool execution."""
    tool_id: str = ""
    tool_name: str
    is_success: bool
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    execution_time_ms: float = 0.0
    is_sandboxed: bool = True


class BaseTool(ABC):
    """Abstract base class for all registered JARVIS tools."""

    def __init__(self, definition: ToolDefinition) -> None:
        self.definition = definition

    @property
    def metadata(self) -> ToolDefinition:
        """Compatibility property."""
        return self.definition

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        """Execute the tool safely within sandbox boundaries."""
        pass
