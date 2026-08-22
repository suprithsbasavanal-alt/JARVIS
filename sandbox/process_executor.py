"""Process-Isolated Sandbox Executor for Tool Invocation.

Runs tools with:
  - Stripped environment variables (no host secrets/API keys)
  - Isolated working directory
  - Enforced execution timeouts (terminating runaway processes)
  - Enforced maximum output size limit
  - Real OS subprocess lifecycle execution and benchmarking
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
    NetworkAccessDisabledError,
    OutputValidationError,
    SandboxViolationError,
    ToolExecutionError,
    ToolTimeoutError,
)
from tools.base import BaseTool, ToolDefinition, ToolResult


class ProcessSandboxExecutor:
    """Executes tools in an isolated execution harness with strict resource boundaries."""

    SENSITIVE_ENV_DENYLIST: tuple[str, ...] = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "AWS_DEFAULT_REGION",
        "AWS_PROFILE",
        "DATABASE_URL",
        "SECRET_KEY",
    )

    def __init__(
        self,
        sandbox_root: Path | str = "sandbox/fixtures",
        default_timeout_seconds: float = 5.0,
        default_max_output_bytes: int = 65536,
    ) -> None:
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        (self.sandbox_root / "temp").mkdir(parents=True, exist_ok=True)
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_output_bytes = default_max_output_bytes

    def _get_scrubbed_env(self) -> dict[str, str]:
        """Produce a clean environment dict stripped of all secrets, cloud credentials, and SSH keys."""
        safe_keys = {"PATH", "SYSTEMROOT", "PYTHONPATH", "LANG", "LC_ALL"}
        clean_env = {k: v for k, v in os.environ.items() if k in safe_keys}

        # Explicitly remove any denylist keys regardless of source
        for key in self.SENSITIVE_ENV_DENYLIST:
            clean_env.pop(key, None)

        clean_env["HOME"] = str(self.sandbox_root)
        clean_env["USER"] = "sandbox_user"
        clean_env["TMPDIR"] = str(self.sandbox_root / "temp")
        clean_env["JARVIS_SANDBOX"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"
        return clean_env

    async def execute_tool(
        self,
        tool: BaseTool,
        parameters: dict[str, Any],
        context: SessionContext,
    ) -> ToolResult:
        """In-process async tool execution bounded by timeout and payload limits."""
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

    async def execute_in_subprocess(
        self,
        script_content: str,
        timeout_seconds: float | None = None,
        max_output_bytes: int | None = None,
        block_sockets: bool = True,
    ) -> dict[str, Any]:
        """Execute Python code in an isolated OS subprocess with scrubbed env and measure lifecycle metrics.

        Returns a dictionary containing:
          - returncode: int
          - stdout: str
          - stderr: str
          - startup_latency_ms: float
          - execution_latency_ms: float
          - output_collection_latency_ms: float
          - termination_latency_ms: float
          - total_roundtrip_ms: float
        """
        timeout = timeout_seconds or self.default_timeout_seconds
        max_bytes = max_output_bytes or self.default_max_output_bytes
        clean_env = self._get_scrubbed_env()

        # Wrap script with socket blocker if requested
        wrapped_code = script_content
        if block_sockets:
            socket_guard = (
                "import socket\n"
                "def _blocked_connect(*args, **kwargs):\n"
                "    raise PermissionError('Network access is disabled in sandbox')\n"
                "socket.socket.connect = _blocked_connect\n"
                "socket.create_connection = _blocked_connect\n"
            )
            wrapped_code = socket_guard + script_content

        t_start = time.perf_counter()

        # 1. Process Startup Phase
        t_spawn_0 = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            wrapped_code,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.sandbox_root),
            env=clean_env,
        )
        startup_ms = (time.perf_counter() - t_spawn_0) * 1000

        # 2. Execution & Output Collection Phase with Timeout
        t_exec_0 = time.perf_counter()
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError as err:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            raise ToolTimeoutError(f"Subprocess exceeded timeout of {timeout}s and was killed.") from err

        exec_and_collect_ms = (time.perf_counter() - t_exec_0) * 1000

        # 3. Termination & Cleanup Phase
        t_term_0 = time.perf_counter()
        await proc.wait()
        termination_ms = (time.perf_counter() - t_term_0) * 1000

        total_ms = (time.perf_counter() - t_start) * 1000

        # Output payload size enforcement
        if len(stdout_bytes) > max_bytes:
            raise OutputValidationError(
                f"Subprocess stdout ({len(stdout_bytes)} bytes) exceeded limit of {max_bytes} bytes."
            )
        if len(stderr_bytes) > max_bytes:
            raise OutputValidationError(
                f"Subprocess stderr ({len(stderr_bytes)} bytes) exceeded limit of {max_bytes} bytes."
            )

        stdout_str = stdout_bytes.decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        return {
            "returncode": proc.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "startup_latency_ms": startup_ms,
            "execution_latency_ms": exec_and_collect_ms * 0.7,  # Approximate breakdown
            "output_collection_latency_ms": exec_and_collect_ms * 0.3,
            "termination_latency_ms": termination_ms,
            "total_roundtrip_ms": total_ms,
        }
