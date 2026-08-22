"""Base Tool Interfaces and Capability Declarations."""

from abc import ABC, abstractmethod
from typing import Any
from core.compat import BaseModel, Field
from config.schema import PermissionLevel
from core.context import SessionContext
from core.types import ActionCategory


class ToolMetadata(BaseModel):
    """Metadata and capability declaration for a tool."""
    name: str
    description: str
    action_category: ActionCategory
    required_permission_level: PermissionLevel
    parameter_schema: dict[str, Any]
    is_sandboxed_only: bool = True
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class ToolResult(BaseModel):
    """Encapsulates output of tool execution."""
    tool_name: str
    is_success: bool
    output_data: Any = None
    error_message: str | None = None
    execution_time_ms: float = 0.0


class BaseTool(ABC):
    """Abstract base class for all JARVIS tools."""

    def __init__(self, metadata: ToolMetadata) -> None:
        self.metadata = metadata

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        """Execute the tool logic."""
        pass
