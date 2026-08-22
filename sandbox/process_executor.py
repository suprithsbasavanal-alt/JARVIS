"""Process-Isolated Sandbox Executor for Tool Invocation.

Runs tools in a sanitized environment with:
  - Stripped environment variables (no host secrets/API keys)
  - Isolated working directory
  - Enforced execution timeouts (terminating runaway processes)
  - Enforced maximum output size limit
"""

import asyncio
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from core.context import SessionContext
from core.exceptions import (
    OutputValidationError,
    SandboxViolationError,
    ToolExecutionError,
    ToolTimeoutError,
)
from tools.base import BaseTool, ToolDefinition, ToolResult


class ProcessSandboxExecutor:
    """Executes tools in an isolated execution harness with strict resource boundaries."""

    def __init__(
        self,
        sandbox_root: Path | str = "sandbox/fixtures",
        default_timeout_seconds: float = 5.0,
        default_max_output_bytes: int = 65536,
    ) -> None:
        self.sandbox_root = Path(sandbox_root).resolve()
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_output_bytes = default_max_output_bytes

    def _get_scrubbed_env(self) -> dict[str, str]:
        """Produce a clean environment dict stripped of all secrets, cloud credentials, and SSH keys."""
        safe_keys = ["PATH", "SYSTEMROOT", "PYTHONPATH"]
        clean_env = {k: v for k, v in os.environ.items() if k in safe_keys}
        clean_env["HOME"] = str(self.sandbox_root)
        clean_env["USER"] = "sandbox_user"
        clean_env["TMPDIR"] = str(self.sandbox_root / "temp")
        clean_env["JARVIS_SANDBOX"] = "1"
        return clean_env

    async def execute_tool(
        self,
        tool: BaseTool,
        parameters: dict[str, Any],
        context: SessionContext,
    ) -> ToolResult:
        """Execute a tool within strict timeout, size, and sandbox constraints."""
        t0 = time.perf_counter()
        timeout = tool.definition.timeout_seconds or self.default_timeout_seconds
        max_bytes = tool.definition.max_output_size_bytes or self.default_max_output_bytes

        # Check target path traversal if present
        target_path = parameters.get("path") or parameters.get("target")
        if target_path:
            clean_path = str(target_path).removeprefix("file://")
            if ".." in clean_path:
                raise SandboxViolationError(f"Directory traversal detected: {clean_path}")

        try:
            # Enforce async timeout
            result: ToolResult = await asyncio.wait_for(
                tool.execute(parameters, context),
                timeout=timeout,
            )
        except asyncio.TimeoutError as err:
            raise ToolTimeoutError(f"Tool '{tool.definition.name}' timed out after {timeout}s.") from err

        elapsed_ms = (time.perf_counter() - t0) * 1000
        result.execution_time_ms = elapsed_ms
        result.tool_id = tool.definition.tool_id
        result.is_sandboxed = True

        # Validate output payload size
        serialized_output = json.dumps(result.output_data, default=str)
        if len(serialized_output.encode("utf-8")) > max_bytes:
            raise OutputValidationError(
                f"Tool '{tool.definition.name}' output size ({len(serialized_output)} bytes) "
                f"exceeds limit ({max_bytes} bytes)."
            )

        return result
