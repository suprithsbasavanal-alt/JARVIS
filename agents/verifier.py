"""Deterministic Tool Output Verifier and Content Isolator for Phase 3 and Phase 4.1."""

import json
from typing import Any
from core.exceptions import OutputValidationError
from tools.base import ToolCapability, ToolDefinition, ToolResult


class OutputVerifier:
    """Validates tool execution output schemas and wraps untrusted output in safety tags."""

    def verify_tool_result(
        self,
        result: ToolResult,
        definition: ToolDefinition | None = None,
    ) -> str:
        """Validate output schema and return safe XML-tagged serialized output."""
        if not result.is_success:
            err_msg = result.error_message or "Tool execution failed."
            return (
                f"<untrusted_tool_output tool=\"{result.tool_name}\" status=\"ERROR\">\n"
                f"{err_msg}\n"
                f"</untrusted_tool_output>"
            )

        # Validate against output schema if provided
        if definition and definition.output_schema:
            schema = definition.output_schema
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in result.output_data:
                    raise OutputValidationError(
                        f"Tool '{definition.name}' output missing required field '{field}'."
                    )

        # Special isolation tag for web research content
        is_web_research = (
            result.tool_name in ("web_fetch", "web_search")
            or (definition and definition.capability == ToolCapability.RESEARCH)
        )

        if is_web_research and result.tool_name == "web_fetch":
            url_str = result.output_data.get("url", "unknown")
            title_str = result.output_data.get("title", "Untitled")
            content_str = result.output_data.get("content", "")
            return (
                f"<untrusted_web_content url=\"{url_str}\" title=\"{title_str}\" status=\"SUCCESS\">\n"
                f"{content_str}\n"
                f"</untrusted_web_content>"
            )

        serialized = json.dumps(result.output_data, indent=2, default=str)

        # Wrap in untrusted tool output tags for prompt injection defense
        return (
            f"<untrusted_tool_output tool=\"{result.tool_name}\" status=\"SUCCESS\">\n"
            f"{serialized}\n"
            f"</untrusted_tool_output>"
        )
