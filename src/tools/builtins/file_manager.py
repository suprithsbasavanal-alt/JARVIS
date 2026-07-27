"""File Manager Tool Implementation."""

import os
import time
from typing import Any
from src.tools.contracts.tool import BaseTool, ToolMetadata, ToolResult


class FileManagerTool(BaseTool):
    """Safely inspects file contents within workspace bounds."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="file_manager",
            description="Reads file contents or lists directory files safely.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "list"]},
                    "path": {"type": "string", "description": "Target file or directory path"}
                },
                "required": ["action", "path"]
            }
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        start_time = time.time()
        action = kwargs.get("action")
        target_path = kwargs.get("path", ".")

        try:
            if action == "read":
                if not os.path.exists(target_path):
                    return ToolResult(
                        tool_name="file_manager",
                        success=False,
                        output=None,
                        error=f"File not found: {target_path}"
                    )
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return ToolResult(
                    tool_name="file_manager",
                    success=True,
                    output=content,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2)
                )
            elif action == "list":
                if not os.path.exists(target_path):
                    return ToolResult(
                        tool_name="file_manager",
                        success=False,
                        output=None,
                        error=f"Directory not found: {target_path}"
                    )
                entries = os.listdir(target_path)
                return ToolResult(
                    tool_name="file_manager",
                    success=True,
                    output=entries,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2)
                )
            else:
                return ToolResult(
                    tool_name="file_manager",
                    success=False,
                    output=None,
                    error=f"Unsupported file action: '{action}'"
                )
        except Exception as e:
            return ToolResult(
                tool_name="file_manager",
                success=False,
                output=None,
                error=f"File operation failed: {str(e)}"
            )
