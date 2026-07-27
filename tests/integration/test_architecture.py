"""Integration Test Suite for Jarvis Architecture Modules."""

import pytest
from src.tools.contracts.tool import BaseTool, ToolMetadata, ToolResult


class DummySearchTool(BaseTool):
    """Dummy tool testing Open/Closed Principle compliance."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="dummy_search",
            description="Searches test vector index",
            parameters_schema={"type": "object"}
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            tool_name="dummy_search",
            success=True,
            output=["Result 1", "Result 2"]
        )


@pytest.mark.asyncio
async def test_tool_contract_execution():
    """Verifies tools interface contract."""
    tool = DummySearchTool()
    assert tool.metadata.name == "dummy_search"
    res = await tool.execute()
    assert res.success is True
    assert len(res.output) == 2
