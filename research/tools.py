"""Typed Capability Tools for Web Search and Content Retrieval for Phase 4.1."""

from typing import Any
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import MalformedToolRequestError, UnknownParameterError
from research.fetcher import SafeWebFetcher
from research.url_validator import URLValidator
from tools.base import (
    BaseTool,
    RiskLevel,
    SideEffectLevel,
    ToolCapability,
    ToolDefinition,
    ToolResult,
)


class WebSearchTool(BaseTool):
    """Hermetic web search tool querying simulated sandbox search fixtures or web APIs."""

    def __init__(self, mock_results: dict[str, list[dict[str, str]]] | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="web_search",
                name="web_search",
                description="Performs safe, sandboxed web searches for factual queries.",
                version="1.0.0",
                capability=ToolCapability.RESEARCH,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query keywords"},
                        "limit": {"type": "integer", "description": "Max results to return (1-10)"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "result_count": {"type": "integer"},
                        "results": {"type": "array"},
                    },
                    "required": ["query", "result_count", "results"],
                },
            )
        )
        self.mock_results = mock_results or {}

    def register_mock_search(self, query_keyword: str, results: list[dict[str, str]]) -> None:
        """Register canned search results for hermetic sandbox testing."""
        self.mock_results[query_keyword.lower()] = results

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"query", "limit"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for web search: {unknown}")

        query = parameters.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            raise MalformedToolRequestError("Missing or invalid 'query' parameter.")

        limit = int(parameters.get("limit", 5))
        clean_query = query.strip()
        q_lower = clean_query.lower()

        # Find matching mock results
        matching_results: list[dict[str, str]] = []
        for kw, res_list in self.mock_results.items():
            if kw in q_lower or q_lower in kw:
                matching_results.extend(res_list)

        if not matching_results:
            # Fallback simulated search result
            matching_results = [
                {
                    "title": f"Information on {clean_query}",
                    "snippet": f"Overview and verified technical details regarding {clean_query}.",
                    "url": f"https://en.wikipedia.org/wiki/{clean_query.replace(' ', '_')}",
                }
            ]

        results = matching_results[:limit]

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=True,
            output_data={
                "query": clean_query,
                "result_count": len(results),
                "results": results,
            },
        )


class WebPageReaderTool(BaseTool):
    """Safe read-only web page extractor with strict SSRF and content isolation."""

    def __init__(self, fetcher: SafeWebFetcher | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="web_fetch",
                name="web_fetch",
                description="Fetches and extracts clean Markdown content from an HTTP/HTTPS URL.",
                version="1.0.0",
                capability=ToolCapability.RESEARCH,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target HTTP/HTTPS URL to fetch"}
                    },
                    "required": ["url"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "bytes": {"type": "integer"},
                    },
                    "required": ["url", "title", "content", "bytes"],
                },
            )
        )
        self.fetcher = fetcher or SafeWebFetcher()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"url"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for web fetch: {unknown}")

        raw_url = parameters.get("url")
        if not raw_url or not isinstance(raw_url, str):
            raise MalformedToolRequestError("Missing or invalid 'url' parameter.")

        try:
            doc = await self.fetcher.fetch_url(raw_url)
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={
                    "url": doc.url,
                    "title": doc.title,
                    "content": doc.markdown_content,
                    "bytes": doc.raw_byte_length,
                },
            )
        except Exception as err:
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=False,
                error_message=f"Web fetch blocked or failed: {err}",
            )
