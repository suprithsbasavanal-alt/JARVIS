"""Typed Web Search Provider Abstraction and Mock Implementation for Phase 4.2."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any
from urllib.parse import urlparse
from core.compat import BaseModel, Field
from core.exceptions import ToolTimeoutError
from research.ssrf import SSRFGuard
from research.url_validator import URLValidator


class SearchResultItem(BaseModel):
    """Structured, validated search result item."""
    title: str
    url: str
    domain: str
    snippet: str
    rank: int


class SearchResponse(BaseModel):
    """Standardized search response container."""
    query: str
    total_results: int
    results: list[SearchResultItem] = Field(default_factory=list)


class BaseSearchProvider(ABC):
    """Abstract interface for all web search providers."""

    def __init__(self, provider_name: str = "base_search") -> None:
        self.provider_name = provider_name

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 5,
        timeout_seconds: float = 5.0,
    ) -> SearchResponse:
        """Execute a search query and return validated SearchResponse."""
        pass


class MockSearchProvider(BaseSearchProvider):
    """Hermetic, deterministic search provider backed by static fixtures for safe testing."""

    def __init__(self) -> None:
        super().__init__(provider_name="mock_search_engine")
        self._fixtures: dict[str, list[dict[str, Any]]] = {}
        self._hang_seconds: float = 0.0

    def set_hang_timeout(self, seconds: float) -> None:
        """Simulate a hanging provider for timeout testing."""
        self._hang_seconds = seconds

    def register_fixture(self, keyword: str, results: list[dict[str, Any]]) -> None:
        """Register canned search results for a given query keyword."""
        self._fixtures[keyword.strip().lower()] = results

    async def search(
        self,
        query: str,
        limit: int = 5,
        timeout_seconds: float = 5.0,
    ) -> SearchResponse:
        """Execute mock search query with per-result URL & SSRF validation."""
        if self._hang_seconds > 0:
            await asyncio.sleep(self._hang_seconds)

        clean_query = query.strip()
        q_lower = clean_query.lower()
        clamped_limit = max(1, min(limit, 10))

        raw_candidates: list[dict[str, Any]] = []

        # Find matching registered fixture
        for kw, res_list in self._fixtures.items():
            if kw in q_lower or q_lower in kw:
                raw_candidates.extend(res_list)

        # Fallback deterministic synthetic results if no fixture matches
        if not raw_candidates:
            slug = clean_query.replace(" ", "_").lower()
            raw_candidates = [
                {
                    "title": f"Verified Technical Overview: {clean_query}",
                    "url": f"https://en.wikipedia.org/wiki/{slug}",
                    "snippet": f"Comprehensive encyclopedia documentation and verified reference regarding {clean_query}.",
                },
                {
                    "title": f"Official Research & Specifications: {clean_query}",
                    "url": f"https://docs.python.org/3/search.html?q={slug}",
                    "snippet": f"Standard language documentation and formal specifications for {clean_query}.",
                },
            ]

        # Validate and structure each candidate result through URL & SSRF security filter
        validated_items: list[SearchResultItem] = []
        for idx, item in enumerate(raw_candidates):
            raw_url = item.get("url", "")
            raw_title = str(item.get("title", "Untitled"))
            raw_snippet = str(item.get("snippet", ""))

            # 1. Strict URL syntax and scheme validation
            try:
                norm_url = URLValidator.validate_and_normalize(raw_url)
            except Exception:
                # Malicious or invalid URL format; drop from results
                continue

            # 2. Strict SSRF check on destination IP / host
            try:
                SSRFGuard.validate_url_for_ssrf(norm_url)
            except Exception:
                # Private IP / metadata / loopback result; drop from results
                continue

            # 3. Extract domain cleanly
            parsed = urlparse(norm_url)
            domain = parsed.hostname or "unknown"

            validated_items.append(
                SearchResultItem(
                    title=raw_title,
                    url=norm_url,
                    domain=domain,
                    snippet=raw_snippet,
                    rank=len(validated_items) + 1,
                )
            )

            if len(validated_items) >= clamped_limit:
                break

        return SearchResponse(
            query=clean_query,
            total_results=len(validated_items),
            results=validated_items,
        )
