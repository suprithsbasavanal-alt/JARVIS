"""Unit tests for AgentLoop execution flow."""

from typing import Any
import pytest
from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError
from core.types import ActionCategory
from tools.base import BaseTool, ToolMetadata, ToolResult
from tools.registry import ToolRegistry


class MockSafeTool(BaseTool):
    """Mock safe tool for testing."""
    def __init__(self) -> None:
        super().__init__(
            ToolMetadata(
                name="read_mock_note",
                description="Reads a mock note",
                action_category=ActionCategory.SAFE,
                required_permission_level=PermissionLevel.NORMAL,
                parameter_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            )
        )

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        return ToolResult(tool_name=self.metadata.name, is_success=True, output_data="Mock note content.")


class MockSensitiveTool(BaseTool):
    """Mock sensitive tool for testing confirmation gate."""
    def __init__(self) -> None:
        super().__init__(
            ToolMetadata(
                name="dispatch_mock_email",
                description="Sends an email",
                action_category=ActionCategory.SENSITIVE,
                required_permission_level=PermissionLevel.SENSITIVE,
                parameter_schema={"type": "object", "properties": {"recipient": {"type": "string"}}},
            )
        )

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        return ToolResult(tool_name=self.metadata.name, is_success=True, output_data="Email dispatched.")


@pytest.mark.asyncio
async def test_agent_loop_conversational_turn(agent_loop: AgentLoop, session_context: SessionContext) -> None:
    """Verify purely conversational query completes and logs audit entry."""
    response = await agent_loop.process_turn("What is the speed of light?", session_context)
    assert response.content != ""
    assert len(agent_loop.audit.get_entries()) == 1


@pytest.mark.asyncio
async def test_agent_loop_sensitive_tool_triggers_confirmation(
    agent_loop: AgentLoop, session_context: SessionContext
) -> None:
    """Verify sensitive tool without approval token raises HumanConfirmationRequiredError."""
    # Register sensitive tool
    sensitive_tool = MockSensitiveTool()
    agent_loop.tool_registry.register(sensitive_tool)

    # Configure mock provider to trigger tool call on 'send'
    from model_routing.providers.mock_provider import MockModelProvider
    from model_routing.schemas import ModelTier, ToolCallDefinition
    mock_prov = agent_loop.router.get_provider_for_tier(ModelTier.FAST)
    if isinstance(mock_prov, MockModelProvider):
        mock_prov.register_tool_trigger(
            "send",
            ToolCallDefinition(
                tool_name="dispatch_mock_email",
                arguments={"recipient": "test@example.com"},
            ),
        )

    with pytest.raises(HumanConfirmationRequiredError):
        await agent_loop.process_turn("Please send the update email", session_context)
