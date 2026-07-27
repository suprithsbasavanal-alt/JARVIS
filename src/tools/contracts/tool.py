"""Abstract Base Classes for Tools & Execution Sandbox (SOLID - OCP / LSP)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    """Metadata describing tool capabilities and input schemas for LLM usage."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    requires_approval: bool = False


class ToolResult(BaseModel):
    """Normalized tool execution response."""
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseTool(ABC):
    """Abstract Base Class for all Jarvis extension tools."""

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Returns metadata and JSON schema for tool invocation."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes tool logic asynchronously."""
        pass


class ToolSandboxContract(ABC):
    """Abstract Interface for Sandboxed Code Execution."""

    @abstractmethod
    async def run_code(self, code: str, timeout_seconds: int = 30) -> ToolResult:
        """Runs isolated code block within secure container sandbox."""
        pass
