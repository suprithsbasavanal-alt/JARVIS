"""Typed Capability Tools for Web Search and Content Retrieval for Phase 4.1 and Phase 4.2."""

from typing import Any
from urllib.parse import urlparse
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import MalformedToolRequestError, UnknownParameterError
from research.fetcher import SafeWebFetcher
from research.search_provider import (
    BaseSearchProvider,
    MockSearchProvider,
    SearchResultItem,
)
from research.ssrf import SSRFGuard
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
    """Hermetic web search tool querying typed search providers with SSRF and size bounds."""

    MAX_QUERY_LENGTH = 500

    def __init__(
        self,
        provider: BaseSearchProvider | None = None,
        mock_results: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="web_search",
                name="web_search",
                description="Performs safe, sandboxed web searches for factual queries.",
                version="1.1.0",
                capability=ToolCapability.RESEARCH,
                permission_tier=PermissionLevel.NORMAL,
                risk_level=RiskLevel.LOW,
                allowed_environment="SANDBOX_ONLY",
                requires_confirmation=False,
                side_effect_level=SideEffectLevel.READ,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query keywords (max 500 characters)",
                            "maxLength": 500,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results to return (1-10)",
                            "minimum": 1,
                            "maximum": 10,
                        },
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
        if provider:
            self.provider = provider
        else:
            mock_p = MockSearchProvider()
            if mock_results:
                for kw, res in mock_results.items():
                    mock_p.register_fixture(kw, res)
            self.provider = mock_p

    def register_mock_search(self, query_keyword: str, results: list[dict[str, Any]]) -> None:
        """Register canned search results for hermetic sandbox testing."""
        if isinstance(self.provider, MockSearchProvider):
            self.provider.register_fixture(query_keyword, results)

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"query", "limit"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for web search: {unknown}")

        raw_query = parameters.get("query")
        if raw_query is None or not isinstance(raw_query, str):
            raise MalformedToolRequestError("Missing or invalid 'query' parameter.")

        clean_query = raw_query.strip()
        if not clean_query:
            raise MalformedToolRequestError("Search query cannot be empty or whitespace only.")

        if len(clean_query) > self.MAX_QUERY_LENGTH:
            raise MalformedToolRequestError(
                f"Search query length ({len(clean_query)}) exceeds maximum limit of {self.MAX_QUERY_LENGTH} characters."
            )

        raw_limit = parameters.get("limit", 5)
        try:
            limit = int(raw_limit)
        except (ValueError, TypeError) as err:
            raise MalformedToolRequestError(f"Invalid limit parameter '{raw_limit}'.") from err

        clamped_limit = max(1, min(limit, 10))

        try:
            search_response = await self.provider.search(clean_query, limit=clamped_limit)
            
            # Serialize SearchResultItems cleanly into dicts
            results_dicts: list[dict[str, Any]] = []
            for item in search_response.results:
                if isinstance(item, SearchResultItem):
                    results_dicts.append(item.model_dump())
                elif isinstance(item, dict):
                    # Ensure domain and rank are present
                    norm_url = item.get("url", "")
                    domain = urlparse(norm_url).hostname or "unknown"
                    results_dicts.append({
                        "title": item.get("title", "Untitled"),
                        "url": norm_url,
                        "domain": item.get("domain", domain),
                        "snippet": item.get("snippet", ""),
                        "rank": item.get("rank", len(results_dicts) + 1),
                    })

            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={
                    "query": search_response.query,
                    "result_count": len(results_dicts),
                    "results": results_dicts,
                },
            )
        except Exception as err:
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=False,
                error_message=f"Search provider error: {err}",
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


class DocumentParserTool(BaseTool):
    """Safe PDF and Markdown document parser with citation extraction and sandbox bounding."""

    def __init__(self, engine: Any | None = None) -> None:
        super().__init__(
            ToolDefinition(
                tool_id="document_parse",
                name="document_parse",
                description="Safely parses PDF and Markdown documents, extracting text and verifiable citations.",
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
                        "file_path": {
                            "type": "string",
                            "description": "Relative or sandbox path to the document file (PDF or Markdown)",
                        },
                        "extract_citations": {
                            "type": "boolean",
                            "description": "Whether to extract granular section/page citations",
                            "default": True,
                        },
                    },
                    "required": ["file_path"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "title": {"type": "string"},
                        "document_type": {"type": "string"},
                        "content_hash": {"type": "string"},
                        "byte_size": {"type": "integer"},
                        "page_or_section_count": {"type": "integer"},
                        "full_text": {"type": "string"},
                        "citations": {"type": "array"},
                    },
                    "required": [
                        "file_path",
                        "title",
                        "document_type",
                        "content_hash",
                        "byte_size",
                        "page_or_section_count",
                        "full_text",
                        "citations",
                    ],
                },
            )
        )
        from research.document_engine import DocumentEngine
        self.engine = engine or DocumentEngine()

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        allowed_keys = {"file_path", "extract_citations"}
        if not set(parameters.keys()).issubset(allowed_keys):
            unknown = set(parameters.keys()) - allowed_keys
            raise UnknownParameterError(f"Unknown parameters for document parser: {unknown}")

        raw_path = parameters.get("file_path")
        if not raw_path or not isinstance(raw_path, str) or not raw_path.strip():
            raise MalformedToolRequestError("Missing or invalid 'file_path' parameter.")

        extract_citations = bool(parameters.get("extract_citations", True))
        clean_path = raw_path.strip()

        try:
            doc = await self.engine.parse_document(
                file_path=clean_path,
                extract_citations=extract_citations,
                allowed_dirs=context.active_whitelist_paths,
            )

            # Serialize citations cleanly
            citations_data = [cite.model_dump() for cite in doc.citations]

            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=True,
                output_data={
                    "file_path": doc.source_uri,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "content_hash": doc.content_hash,
                    "byte_size": doc.byte_size,
                    "page_or_section_count": doc.page_or_section_count,
                    "full_text": doc.full_text,
                    "citations": citations_data,
                },
            )
        except Exception as err:
            return ToolResult(
                tool_id=self.definition.tool_id,
                tool_name=self.definition.name,
                is_success=False,
                error_message=f"Document parsing failed: {err}",
            )

