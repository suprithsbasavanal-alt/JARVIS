"""Phase 4.1 & 4.2 Secure Web Research & Search Engine Package."""

from research.fetcher import FetchedWebDocument, SafeWebFetcher
from research.normalizer import HTMLNormalizer
from research.search_provider import (
    BaseSearchProvider,
    MockSearchProvider,
    SearchResponse,
    SearchResultItem,
)
from research.ssrf import SSRFGuard
from research.tools import WebPageReaderTool, WebSearchTool
from research.url_validator import URLValidator

__all__ = [
    "BaseSearchProvider",
    "FetchedWebDocument",
    "HTMLNormalizer",
    "MockSearchProvider",
    "SSRFGuard",
    "SafeWebFetcher",
    "SearchResponse",
    "SearchResultItem",
    "URLValidator",
    "WebPageReaderTool",
    "WebSearchTool",
]
