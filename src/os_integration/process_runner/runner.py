"""Safe Subprocess Execution Runner."""

import asyncio
from typing import Dict, Any
from src.shared.logger.logger import get_logger

logger = get_logger("os_integration.process_runner")


class SystemProcessRunner:
    """Safe host process command launcher with timeout enforcement."""

    async def run_command(self, command: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        """Executes system shell command returning exit code, stdout, and stderr."""
        logger.info(f"Executing system process command: '{command}' (timeout: {timeout_seconds}s)...")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds
            )
            return {
                "exit_code": proc.returncode,
                "stdout": stdout_bytes.decode("utf-8").strip(),
                "stderr": stderr_bytes.decode("utf-8").strip(),
                "success": proc.returncode == 0
            }
        except asyncio.TimeoutError:
            logger.error(f"Process execution timed out after {timeout_seconds}s: '{command}'")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Process execution timed out after {timeout_seconds} seconds.",
                "success": False
            }
