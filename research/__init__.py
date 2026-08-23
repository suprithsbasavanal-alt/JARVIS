"""Phase 4 Complete Web & Research Engine Package."""

from research.citation import CitationManager, CitationSource
from research.document_engine import DocumentEngine, ParsedDocument
from research.fetcher import FetchedWebDocument, SafeWebFetcher
from research.markdown_parser import SecureMarkdownParser
from research.normalizer import HTMLNormalizer, TextNormalizer
from research.pdf_parser import SecurePDFParser
from research.search_provider import (
    BaseSearchProvider,
    MockSearchProvider,
    SearchResponse,
    SearchResultItem,
)
from research.ssrf import SSRFGuard
from research.tools import DocumentParserTool, WebPageReaderTool, WebSearchTool
from research.url_validator import URLValidator

__all__ = [
    "BaseSearchProvider",
    "CitationManager",
    "CitationSource",
    "DocumentEngine",
    "DocumentParserTool",
    "FetchedWebDocument",
    "HTMLNormalizer",
    "MockSearchProvider",
    "ParsedDocument",
    "SSRFGuard",
    "SafeWebFetcher",
    "SearchResponse",
    "SearchResultItem",
    "SecureMarkdownParser",
    "SecurePDFParser",
    "TextNormalizer",
    "URLValidator",
    "WebPageReaderTool",
    "WebSearchTool",
]
