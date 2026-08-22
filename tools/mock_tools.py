"""Mock Tools Framework for Phase 1 Safe Development & Testing.

All mock tools operate exclusively within sandbox/fixtures/ with zero host or network access.
"""

from typing import Any
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import MalformedToolRequestError
from core.types import ActionCategory
from sandbox.environment import SandboxEnvironment
from tools.base import BaseTool, ToolMetadata, ToolResult


class MockCalculatorTool(BaseTool):
    """Safe arithmetic computation tool."""

    def __init__(self) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_calculator",
                description="Performs basic arithmetic calculations safely.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "e.g. 2 + 2 or 10 * 5"}
                    },
                    "required": ["expression"],
                },
                is_sandboxed_only=True,
            )
        )

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        expr = parameters.get("expression")
        if not expr or not isinstance(expr, str):
            raise MalformedToolRequestError("Parameter 'expression' is missing or invalid.")

        # Safe evaluation of basic mathematical expressions
        allowed_chars = set("0123456789+-*/(). ")
        if not set(expr).issubset(allowed_chars):
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=False,
                error_message="Invalid characters in expression.",
            )

        try:
            # Safe evaluation of mathematical characters only
            # pylint: disable=eval-used
            result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=True,
                output_data={"expression": expr, "result": result},
            )
        except Exception as err:
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=False,
                error_message=f"Computation error: {err}",
            )


class MockFileReaderTool(BaseTool):
    """Safe mock file reader confined strictly to the sandbox."""

    def __init__(self, sandbox_env: SandboxEnvironment | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_file_reader",
                description="Reads file contents from the sandbox virtual filesystem.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Virtual path relative to sandbox"}
                    },
                    "required": ["path"],
                },
                is_sandboxed_only=True,
            )
        )
        self.sandbox_env = sandbox_env or SandboxEnvironment()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        rel_path = parameters.get("path")
        if not rel_path or not isinstance(rel_path, str):
            raise MalformedToolRequestError("Parameter 'path' is missing or invalid.")

        try:
            content = self.sandbox_env.fs.read_file(rel_path)
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=True,
                output_data={"path": rel_path, "content": content},
            )
        except Exception as err:
            return ToolResult(
                tool_name=self.metadata.name,
                is_success=False,
                error_message=str(err),
            )


class MockCalendarReaderTool(BaseTool):
    """Safe mock calendar reader backed by static fixtures."""

    def __init__(self, sandbox_env: SandboxEnvironment | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_calendar_reader",
                description="Reads upcoming events from the mock calendar fixture.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {"type": "integer", "description": "Number of days ahead to search"}
                    },
                },
                is_sandboxed_only=True,
            )
        )
        self.sandbox_env = sandbox_env or SandboxEnvironment()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        days = int(parameters.get("days_ahead", 7))
        events = await self.sandbox_env.calendar_service.list_upcoming_events(days_ahead=days)
        return ToolResult(
            tool_name=self.metadata.name,
            is_success=True,
            output_data={"event_count": len(events), "events": [e.model_dump() for e in events]},
        )


class MockEmailDraftTool(BaseTool):
    """Safe mock email draft creator."""

    def __init__(self, sandbox_env: SandboxEnvironment | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_email_draft",
                description="Creates an email draft in the mock email service.",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "subject": {"type": "string"},
                        "body_text": {"type": "string"},
                    },
                    "required": ["recipient", "subject", "body_text"],
                },
                is_sandboxed_only=True,
            )
        )
        self.sandbox_env = sandbox_env or SandboxEnvironment()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        recipient = parameters.get("recipient")
        subject = parameters.get("subject")
        body_text = parameters.get("body_text")

        if not recipient or not subject or not body_text:
            raise MalformedToolRequestError("Missing required parameters for email draft.")

        from integrations.contracts.email import EmailDraft
        draft = EmailDraft(recipient=recipient, subject=subject, body_text=body_text)
        draft_id = await self.sandbox_env.email_service.create_draft(draft)

        return ToolResult(
            tool_name=self.metadata.name,
            is_success=True,
            output_data={"draft_id": draft_id, "status": "DRAFT_CREATED"},
        )


class MockEmailSenderTool(BaseTool):
    """Sensitive mock email sender that requires explicit confirmation."""

    def __init__(self, sandbox_env: SandboxEnvironment | None = None) -> None:
        super().__init__(
            ToolMetadata(
                name="mock_email_sender",
                description="Dispatches an email draft through the mock email service.",
                action_category=ActionCategory.SENSITIVE,
                required_permission_level=PermissionLevel.SENSITIVE,
                parameter_schema={
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string", "description": "ID of draft to dispatch"},
                        "target_email": {"type": "string", "description": "Recipient address"},
                    },
                    "required": ["draft_id", "target_email"],
                },
                is_sandboxed_only=True,
            )
        )
        self.sandbox_env = sandbox_env or SandboxEnvironment()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        draft_id = parameters.get("draft_id")
        target_email = parameters.get("target_email")

        if not draft_id or not target_email:
            raise MalformedToolRequestError("Missing draft_id or target_email.")

        # In Phase 1: Executes against mock service
        await self.sandbox_env.email_service.send_email(draft_id, "verified-token")
        return ToolResult(
            tool_name=self.metadata.name,
            is_success=True,
            output_data={"status": "SENT", "draft_id": draft_id, "target": target_email},
        )
