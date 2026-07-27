"""Central Tool Registry & Permission Manager (SOLID - OCP / DIP)."""

from typing import Any, Dict, List, Optional
from src.tools.contracts.tool import BaseTool, ToolMetadata, ToolResult
from src.shared.logger.logger import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    """Registry managing dynamic tool discovery and execution."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance into registry (OCP)."""
        name = tool.metadata.name.lower()
        self._tools[name] = tool
        logger.info(f"Registered tool '{name}' into ToolRegistry.")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves tool by name."""
        return self._tools.get(name.lower())

    def list_metadata(self) -> List[ToolMetadata]:
        """Lists metadata schemas for all registered tools."""
        return [tool.metadata for tool in self._tools.values()]

    async def execute_tool(self, name: str, **kwargs: Any) -> ToolResult:
        """Invokes target registered tool with parameters."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                output=None,
                error=f"Tool '{name}' is not registered in ToolRegistry."
            )
        return await tool.execute(**kwargs)
