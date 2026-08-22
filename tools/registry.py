"""Capability-Based Tool Registry."""

from typing import Any
from tools.base import BaseTool


class ToolRegistry:
    """Central catalog and lookup for registered tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool with its capability metadata."""
        self._tools[tool.metadata.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool_schemas_for_model(self) -> list[dict[str, Any]]:
        """Generate JSON tool definitions for model requests."""
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "parameters": tool.metadata.parameter_schema,
                },
            })
        return schemas
