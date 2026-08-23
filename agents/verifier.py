"""Deterministic Tool Output Verifier and Content Isolator for Phase 3 and Phase 4."""

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

        # Isolation tag for web page fetching
        if result.tool_name == "web_fetch":
            url_str = result.output_data.get("url", "unknown")
            title_str = result.output_data.get("title", "Untitled")
            content_str = result.output_data.get("content", "")
            return (
                f"<untrusted_web_content url=\"{url_str}\" title=\"{title_str}\" status=\"SUCCESS\">\n"
                f"{content_str}\n"
                f"</untrusted_web_content>"
            )

        # Isolation tag for web search results
        if result.tool_name == "web_search":
            query_str = result.output_data.get("query", "")
            count_int = result.output_data.get("result_count", len(result.output_data.get("results", [])))
            serialized = json.dumps(result.output_data.get("results", []), indent=2, default=str)
            return (
                f"<untrusted_search_results query=\"{query_str}\" count=\"{count_int}\">\n"
                f"{serialized}\n"
                f"</untrusted_search_results>"
            )

        # Isolation tag for document parsing (PDF & Markdown)
        if result.tool_name == "document_parse":
            path_str = result.output_data.get("file_path", "unknown")
            title_str = result.output_data.get("title", "Untitled Document")
            hash_str = result.output_data.get("content_hash", "")[:16]
            doc_type = result.output_data.get("document_type", "document")
            text_str = result.output_data.get("full_text", "")
            return (
                f"<untrusted_document_content source=\"{path_str}\" title=\"{title_str}\" hash=\"{hash_str}\" type=\"{doc_type}\">\n"
                f"{text_str}\n"
                f"</untrusted_document_content>"
            )

        serialized = json.dumps(result.output_data, indent=2, default=str)

        # Wrap generic tool outputs in untrusted tool output tags
        return (
            f"<untrusted_tool_output tool=\"{result.tool_name}\" status=\"SUCCESS\">\n"
            f"{serialized}\n"
            f"</untrusted_tool_output>"
        )
