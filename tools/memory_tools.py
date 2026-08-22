"""Explicit Memory Capability Tools for JARVIS."""

from typing import Any
from uuid import UUID
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import MalformedToolRequestError
from core.types import ActionCategory
from memory.long_term import MemoryType, SensitivityLevel
from memory.manager import MemoryManager
from tools.base import BaseTool, ToolMetadata, ToolResult


class MockMemoryStoreTool(BaseTool):
    """Explicit user-requested memory storage capability."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_memory_store_tool",
                description="Stores an explicit fact or preference into persistent memory with user consent.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The fact or preference to remember"},
                        "category": {"type": "string", "enum": ["SEMANTIC", "EPISODIC", "SENSITIVE"]},
                        "sensitivity": {"type": "string", "enum": ["NORMAL", "SENSITIVE"]},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["content"],
                },
                is_sandboxed_only=True,
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        if not self.memory_manager:
            return ToolResult(tool_name=self.metadata.name, is_success=False, error_message="Memory manager uninitialized.")

        content = parameters.get("content")
        if not content or not isinstance(content, str):
            raise MalformedToolRequestError("Missing or invalid 'content' parameter.")

        cat_str = parameters.get("category", "SEMANTIC")
        sens_str = parameters.get("sensitivity", "NORMAL")
        tags = parameters.get("tags", [])

        try:
            category = MemoryType(cat_str)
            sensitivity = SensitivityLevel(sens_str)
        except ValueError as err:
            raise MalformedToolRequestError(f"Invalid category or sensitivity: {err}") from err

        record = await self.memory_manager.remember_explicit(
            content=content,
            category=category,
            sensitivity=sensitivity,
            session_id=str(context.session_id),
            tags=tags,
        )

        return ToolResult(
            tool_name=self.metadata.name,
            is_success=True,
            output_data={
                "status": "STORED",
                "memory_id": str(record.memory_id),
                "category": record.category.value,
                "version": record.version,
            },
        )


class MockMemoryRecallTool(BaseTool):
    """Inspect and list memories matching a query."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_memory_recall_tool",
                description="Recalls or searches stored memories for user inspection.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term or topic"},
                    },
                    "required": ["query"],
                },
                is_sandboxed_only=True,
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        if not self.memory_manager:
            return ToolResult(tool_name=self.metadata.name, is_success=False, error_message="Memory manager uninitialized.")

        query = parameters.get("query", "")
        max_sens = (
            SensitivityLevel.SENSITIVE
            if context.permission_level == PermissionLevel.SENSITIVE
            else SensitivityLevel.NORMAL
        )

        records = await self.memory_manager.recall(
            query=query,
            max_sensitivity=max_sens,
            session_id=str(context.session_id),
            limit=5,
        )

        return ToolResult(
            tool_name=self.metadata.name,
            is_success=True,
            output_data={
                "query": query,
                "found_count": len(records),
                "memories": [
                    {
                        "memory_id": str(r.memory_id),
                        "content": r.content,
                        "category": r.category.value,
                        "version": r.version,
                    }
                    for r in records
                ],
            },
        )


class MockMemoryForgetTool(BaseTool):
    """Explicit memory deletion capability."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_memory_forget_tool",
                description="Deletes a specific memory or topic upon user command.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "topic": {"type": "string"},
                    },
                },
                is_sandboxed_only=True,
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        if not self.memory_manager:
            return ToolResult(tool_name=self.metadata.name, is_success=False, error_message="Memory manager uninitialized.")

        mem_id_str = parameters.get("memory_id")
        topic = parameters.get("topic")

        if mem_id_str:
            try:
                mem_id = UUID(mem_id_str)
            except ValueError as err:
                raise MalformedToolRequestError("Invalid UUID for memory_id") from err
            deleted = await self.memory_manager.forget_memory(mem_id, session_id=str(context.session_id))
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=True,
                output_data={"deleted": deleted, "memory_id": mem_id_str},
            )

        if topic:
            count = await self.memory_manager.forget_by_topic(topic, session_id=str(context.session_id))
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=True,
                output_data={"deleted_count": count, "topic": topic},
            )

        raise MalformedToolRequestError("Must specify either 'memory_id' or 'topic' to forget.")
