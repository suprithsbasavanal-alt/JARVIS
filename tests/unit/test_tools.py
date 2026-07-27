"""Unit Test Suite for Tools Component."""

import pytest
from src.tools import (
    CalculatorTool,
    FileManagerTool,
    WebSearchTool,
    ToolRegistry,
    PythonCodeSandbox,
)


@pytest.mark.asyncio
async def test_calculator_tool():
    """Verifies Calculator tool evaluation."""
    calc = CalculatorTool()
    res = await calc.execute(expression="10 + 5 * 2")
    assert res.success is True
    assert res.output == 20.0

    err_res = await calc.execute(expression="invalid syntax + *")
    assert err_res.success is False
    assert "Calculation error" in err_res.error


@pytest.mark.asyncio
async def test_file_manager_tool():
    """Verifies File Manager tool list operation."""
    fm = FileManagerTool()
    res = await fm.execute(action="list", path=".")
    assert res.success is True
    assert isinstance(res.output, list)
    assert "pyproject.toml" in res.output


@pytest.mark.asyncio
async def test_web_search_tool():
    """Verifies Web Search tool results."""
    ws = WebSearchTool()
    res = await ws.execute(query="Clean Architecture")
    assert res.success is True
    assert len(res.output) > 0


@pytest.mark.asyncio
async def test_tool_registry():
    """Verifies ToolRegistry registration and execution."""
    registry = ToolRegistry()
    calc = CalculatorTool()
    registry.register(calc)

    metadata_list = registry.list_metadata()
    assert len(metadata_list) == 1
    assert metadata_list[0].name == "calculator"

    res = await registry.execute_tool("calculator", expression="5 * 5")
    assert res.success is True
    assert res.output == 25.0


@pytest.mark.asyncio
async def test_python_code_sandbox():
    """Verifies Python Code Sandbox execution and stdout capture."""
    sandbox = PythonCodeSandbox()
    code = "result = 42\nprint(f'Computed: {result}')"
    res = await sandbox.run_code(code)
    assert res.success is True
    assert "Computed: 42" in res.output
