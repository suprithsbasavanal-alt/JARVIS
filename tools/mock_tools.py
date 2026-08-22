"""Comprehensive Suite of Strongly Typed Mock Capability Tools for Phase 3."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import MalformedToolRequestError, SandboxViolationError, UnknownParameterError
from memory.long_term import MemoryType, SensitivityLevel
from memory.manager import MemoryManager
from sandbox.mock_fs import MockFileSystem
from tools.base import (
    BaseTool,
    RiskLevel,
    SideEffectLevel,
    ToolCapability,
    ToolDefinition,
    ToolResult,
)


class MockCalculatorTool(BaseTool):
    """Hermetic arithmetic calculation tool."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_calculator",
                name="mock_calculator",
                description="Performs safe mathematical computations.",
                version="1.0.0",
                capability=ToolCapability.COMPUTATION,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.NONE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression (e.g. '2 + 2')"}
                    },
                    "required": ["expression"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"},
                        "result": {"type": "number"},
                    },
                    "required": ["expression", "result"],
                },
            )
        )
        self.mock_fs = mock_fs

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"expression"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for calculator: {unknown}")

        expr = parameters.get("expression")
        if not expr or not isinstance(expr, str):
            raise MalformedToolRequestError("Missing or invalid 'expression' parameter.")

        clean_expr = expr.strip()
        if not all(c in "0123456789+-*/(). %" for c in clean_expr):
            raise MalformedToolRequestError(f"Expression contains invalid characters: '{clean_expr}'")

        try:
            result = float(eval(clean_expr, {"__builtins__": None}, {}))  # noqa: S307
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={"expression": clean_expr, "result": result},
            )
        except Exception as err:
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=False,
                error_message=f"Computation failed: {err}",
            )


class MockFileReaderTool(BaseTool):
    """Confined file reading capability for sandbox fixtures."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_file_reader",
                name="mock_file_reader",
                description="Reads file contents strictly within the sandbox directory.",
                version="1.0.0",
                capability=ToolCapability.FILE_READ,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path inside sandbox/fixtures/"}
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            )
        )
        self.mock_fs = mock_fs or MockFileSystem()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"path"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for file reader: {unknown}")

        path_str = parameters.get("path")
        if not path_str or not isinstance(path_str, str):
            raise MalformedToolRequestError("Missing or invalid 'path' parameter.")

        if ".." in path_str:
            raise SandboxViolationError(f"Path traversal detected: {path_str}")

        clean_path = path_str.removeprefix("sandbox/fixtures/mock_files/").removeprefix("sandbox/fixtures/").removeprefix("sandbox/")
        try:
            fs = getattr(self.mock_fs, "fs", self.mock_fs)
            content = fs.read_file(clean_path)
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={"path": path_str, "content": content},
            )
        except Exception as err:
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=False,
                error_message=f"Could not read sandbox file: {err}",
            )


class MockFileWriterTool(BaseTool):
    """Confined file writing capability for sandbox fixtures."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_file_writer",
                name="mock_file_writer",
                description="Writes file contents strictly within the sandbox directory.",
                version="1.0.0",
                capability=ToolCapability.FILE_WRITE,
                permission_tier=PermissionLevel.SENSITIVE,
                risk_level=RiskLevel.MEDIUM,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=True,
                side_effect_level=SideEffectLevel.WRITE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path inside sandbox/fixtures/"},
                        "content": {"type": "string", "description": "Text content to write"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "bytes_written": {"type": "integer"},
                    },
                    "required": ["path", "bytes_written"],
                },
            )
        )
        self.mock_fs = mock_fs or MockFileSystem()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"path", "content"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for file writer: {unknown}")

        path_str = parameters.get("path")
        content = parameters.get("content")
        if not path_str or not isinstance(path_str, str) or content is None:
            raise MalformedToolRequestError("Missing 'path' or 'content' parameter.")

        if ".." in path_str:
            raise SandboxViolationError(f"Path traversal detected: {path_str}")

        clean_path = path_str.removeprefix("sandbox/fixtures/mock_files/").removeprefix("sandbox/fixtures/").removeprefix("sandbox/")
        fs = getattr(self.mock_fs, "fs", self.mock_fs)
        fs.write_file(clean_path, str(content))

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={"path": path_str, "bytes_written": len(str(content))},
        )


class MockCalendarReaderTool(BaseTool):
    """Static fixture calendar reader."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_calendar_reader",
                name="mock_calendar_reader",
                description="Reads mock calendar events from sandbox fixtures.",
                version="1.0.0",
                capability=ToolCapability.CALENDAR,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Date format YYYY-MM-DD"},
                        "query": {"type": "string", "description": "Optional search term"},
                        "days_ahead": {"type": "integer", "description": "Days ahead to look up"},
                    },
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "event_count": {"type": "integer"},
                        "events": {"type": "array"},
                    },
                    "required": ["date", "event_count", "events"],
                },
            )
        )
        self.mock_fs = mock_fs or MockFileSystem()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"date_str", "query", "days_ahead"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for calendar reader: {unknown}")

        date_str = str(parameters.get("date_str") or parameters.get("query", "2026-08-22"))

        if hasattr(self.mock_fs, "calendar_service"):
            days = int(parameters.get("days_ahead", 7))
            cal_events = await self.mock_fs.calendar_service.list_upcoming_events(days_ahead=days)
            events = [e.dict() if hasattr(e, "dict") else e for e in cal_events]
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={
                    "date": date_str,
                    "event_count": len(events),
                    "events": events,
                },
            )

        try:
            fs = getattr(self.mock_fs, "fs", self.mock_fs)
            raw_json = fs.read_file("mock_calendar_events.json")
            events = json.loads(raw_json)
        except Exception:
            events = [{"title": "Team Sync", "time": "10:00 AM", "date": "2026-08-22"}]

        matching = [e for e in events if e.get("date") == date_str or date_str in str(e) or date_str == "today"]

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={
                "date": date_str,
                "event_count": len(matching) if matching else len(events),
                "events": matching if matching else events,
            },
        )


class MockEmailDraftTool(BaseTool):
    """In-memory mock email draft creator."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_email_draft",
                name="mock_email_draft",
                description="Drafts a simulated email in sandbox memory.",
                version="1.0.0",
                capability=ToolCapability.COMMUNICATION,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.MEDIUM,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.WRITE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["recipient", "subject", "body"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                    },
                    "required": ["status", "recipient", "subject"],
                },
            )
        )
        self.mock_fs = mock_fs

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"recipient", "subject", "body"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for email draft: {unknown}")

        recipient = parameters.get("recipient")
        subject = parameters.get("subject")
        body = parameters.get("body")

        if not recipient or not subject or not body:
            raise MalformedToolRequestError("Missing required email fields.")

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={
                "status": "DRAFT_CREATED",
                "recipient": str(recipient),
                "subject": str(subject),
            },
        )


class MockEmailSenderTool(BaseTool):
    """Simulated external email sender requiring human confirmation."""

    def __init__(self, mock_fs: Any = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_email_sender",
                name="mock_email_sender",
                description="Simulates sending an outbound email. Requires explicit human confirmation.",
                version="1.0.0",
                capability=ToolCapability.COMMUNICATION,
                permission_tier=PermissionLevel.SENSITIVE,
                risk_level=RiskLevel.HIGH,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=True,
                side_effect_level=SideEffectLevel.IRREVERSIBLE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "content": {"type": "string"},
                        "draft_id": {"type": "string"},
                        "target_email": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                    },
                    "required": ["status", "recipient", "subject"],
                },
            )
        )
        self.mock_fs = mock_fs

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"recipient", "subject", "body", "content", "draft_id", "target_email"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for email sender: {unknown}")

        recipient = parameters.get("recipient") or parameters.get("target_email", "user@example.com")
        subject = parameters.get("subject", "Notification")
        body = parameters.get("body") or parameters.get("content", "Simulated email body")

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={
                "status": "SENT",
                "recipient": str(recipient),
                "subject": str(subject),
            },
        )


class MockMemoryStoreTool(BaseTool):
    """Explicit memory storage capability."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_memory_store",
                name="mock_memory_store",
                description="Stores an explicit fact or preference into persistent memory with user consent.",
                version="1.0.0",
                capability=ToolCapability.MEMORY,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.WRITE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The fact or preference to remember"},
                        "category": {"type": "string", "enum": ["SEMANTIC", "EPISODIC", "SENSITIVE"]},
                        "sensitivity": {"type": "string", "enum": ["NORMAL", "SENSITIVE"]},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["content"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "memory_id": {"type": "string"},
                        "category": {"type": "string"},
                        "version": {"type": "integer"},
                    },
                    "required": ["status", "memory_id", "category", "version"],
                },
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"content", "category", "sensitivity", "tags"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for memory store: {unknown}")

        if not self.memory_manager:
            return ToolResult(tool_id=self.definition.tool_id, tool_name=self.definition.name, is_success=False, error_message="Memory manager uninitialized.")

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
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={
                "status": "STORED",
                "memory_id": str(record.memory_id),
                "category": record.category.value,
                "version": record.version,
            },
        )


class MockMemoryRecallTool(BaseTool):
    """Memory recall capability."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_memory_recall",
                name="mock_memory_recall",
                description="Recalls or searches stored memories for user inspection.",
                version="1.0.0",
                capability=ToolCapability.MEMORY,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term or topic"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "found_count": {"type": "integer"},
                        "memories": {"type": "array"},
                    },
                    "required": ["query", "found_count", "memories"],
                },
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"query"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for memory recall: {unknown}")

        if not self.memory_manager:
            return ToolResult(tool_id=self.definition.tool_id, tool_name=self.definition.name, is_success=False, error_message="Memory manager uninitialized.")

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
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
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
    """Memory deletion capability."""

    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="mock_memory_forget",
                name="mock_memory_forget",
                description="Deletes a specific memory or topic upon user command.",
                version="1.0.0",
                capability=ToolCapability.MEMORY,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.MEDIUM,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.IRREVERSIBLE,
                input_schema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "topic": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "deleted": {"type": "boolean"},
                        "deleted_count": {"type": "integer"},
                    },
                },
            )
        )
        self.memory_manager = memory_manager

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"memory_id", "topic"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for memory forget: {unknown}")

        if not self.memory_manager:
            return ToolResult(tool_id=self.definition.tool_id, tool_name=self.definition.name, is_success=False, error_message="Memory manager uninitialized.")

        mem_id_str = parameters.get("memory_id")
        topic = parameters.get("topic")

        if mem_id_str:
            try:
                mem_id = UUID(mem_id_str)
            except ValueError as err:
                raise MalformedToolRequestError("Invalid UUID for memory_id") from err
            deleted = await self.memory_manager.forget_memory(mem_id, session_id=str(context.session_id))
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={"deleted": deleted, "deleted_count": 1 if deleted else 0},
            )

        if topic:
            count = await self.memory_manager.forget_by_topic(topic, session_id=str(context.session_id))
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={"deleted": count > 0, "deleted_count": count},
            )

        raise MalformedToolRequestError("Must specify either 'memory_id' or 'topic' to forget.")
