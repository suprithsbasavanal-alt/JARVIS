"""Strict Capability-Based Tool Registry for Phase 3."""

from typing import Any
from config.schema import PermissionLevel
from core.exceptions import (
    DuplicateToolRegistrationError,
    MalformedToolDefinitionError,
    MalformedToolRequestError,
    ToolNotFoundError,
    UnknownParameterError,
)
from tools.base import BaseTool, ToolCapability, ToolDefinition, ToolResult


class ToolRegistry:
    """Central registry enforcing strict typed contracts, capabilities, and parameters."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a strongly typed tool with contract validation."""
        def_obj = getattr(tool, "definition", getattr(tool, "metadata", None))
        if not def_obj or not def_obj.name:
            raise MalformedToolDefinitionError("Tool definition is missing required 'name' or 'tool_id'.")

        tool_id = getattr(def_obj, "tool_id", def_obj.name)
        if not tool_id:
            raise MalformedToolDefinitionError("Tool must declare a non-empty tool_id.")

        if tool_id in self._tools or def_obj.name in self._tools:
            raise DuplicateToolRegistrationError(f"Tool with identifier '{tool_id}' is already registered.")

        self._tools[tool_id] = tool
        # Also map by name if distinct
        if def_obj.name != tool_id:
            self._tools[def_obj.name] = tool

    def unregister_tool(self, tool_identifier: str) -> bool:
        """Remove a tool from the registry."""
        if tool_identifier in self._tools:
            tool = self._tools[tool_identifier]
            def_obj = tool.definition
            self._tools.pop(def_obj.tool_id, None)
            self._tools.pop(def_obj.name, None)
            return True
        return False

    def get_tool(self, tool_identifier: str) -> BaseTool:
        """Lookup tool by ID or name, raising ToolNotFoundError if absent."""
        tool = self._tools.get(tool_identifier)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_identifier}' is not registered in the ToolRegistry.")
        return tool

    # Aliases for backward compatibility
    register = register_tool
    lookup = get_tool

    def list_tools(
        self,
        capability: ToolCapability | None = None,
        permission_tier: PermissionLevel | None = None,
    ) -> list[ToolDefinition]:
        """List registered tool definitions with optional capability filters."""
        seen_ids: set[str] = set()
        results: list[ToolDefinition] = []

        for tool in self._tools.values():
            def_obj = tool.definition
            if def_obj.tool_id in seen_ids:
                continue
            seen_ids.add(def_obj.tool_id)

            if capability and def_obj.capability != capability:
                continue
            if permission_tier and def_obj.permission_tier != permission_tier:
                continue

            results.append(def_obj)

        return results

    def validate_tool_arguments(self, tool_identifier: str, arguments: dict[str, Any]) -> None:
        """Strict validation of arguments against tool input schema. Fails closed."""
        tool = self.get_tool(tool_identifier)
        schema = tool.definition.input_schema or {}

        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                raise MalformedToolRequestError(f"Missing required parameter '{field}' for tool '{tool.definition.name}'.")

        # If schema disallows additional properties, enforce it strictly
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(arguments.keys()) - set(properties.keys())
            if unknown:
                raise UnknownParameterError(f"Unknown parameters {unknown} passed to tool '{tool.definition.name}'.")

    def get_tool_schemas_for_model(self) -> list[dict[str, Any]]:
        """Export tool definitions as OpenAI-compatible function calling schemas."""
        seen_ids: set[str] = set()
        schemas: list[dict[str, Any]] = []

        for tool in self._tools.values():
            def_obj = tool.definition
            if def_obj.tool_id in seen_ids:
                continue
            seen_ids.add(def_obj.tool_id)

            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": def_obj.name,
                        "description": def_obj.description,
                        "parameters": def_obj.input_schema,
                    },
                }
            )

        return schemas
