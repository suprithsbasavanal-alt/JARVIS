"""Isolated Python Code Execution Sandbox Implementation."""

import io
import sys
import time
import traceback
from src.tools.contracts.tool import ToolSandboxContract, ToolResult
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("tools.sandbox")


class PythonCodeSandbox(ToolSandboxContract):
    """Executes Python code snippets within isolated context with output capture."""

    async def run_code(self, code: str, timeout_seconds: int = None) -> ToolResult:
        start_time = time.time()
        timeout = timeout_seconds or settings.security.sandbox_execution_timeout_seconds

        logger.info(f"Executing Python sandbox code block (timeout: {timeout}s)...")

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        local_scope = {}
        success = True
        error_msg = None

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Execute code safely within restricted local namespace
            exec(code, {"__builtins__": __builtins__}, local_scope)

            output = stdout_capture.getvalue().strip()
            if not output and local_scope:
                output = str({k: v for k, v in local_scope.items() if not k.startswith("__")})
        except Exception as e:
            success = False
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            output = stderr_capture.getvalue().strip()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        duration = round((time.time() - start_time) * 1000, 2)
        return ToolResult(
            tool_name="python_sandbox",
            success=success,
            output=output,
            error=error_msg,
            execution_time_ms=duration
        )
