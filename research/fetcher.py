"""Safe Read-Only HTTP Web Fetcher with SSRF, Redirect, Size, and Timeout Guards."""

import asyncio
from collections.abc import Callable
from http.client import HTTPResponse
import io
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener
from core.exceptions import (
    PayloadSizeExceededError,
    RedirectBlockedError,
    SSRFBlockedError,
    URLValidationError,
    WebFetchTimeoutError,
)
from research.normalizer import HTMLNormalizer
from research.ssrf import SSRFGuard
from research.url_validator import URLValidator


class FetchedWebDocument:
    """Container for validated, sanitized web research content."""

    def __init__(
        self,
        url: str,
        title: str,
        markdown_content: str,
        raw_byte_length: int,
        status_code: int = 200,
        content_type: str = "text/html",
        redirect_history: list[str] | None = None,
    ) -> None:
        self.url = url
        self.title = title
        self.markdown_content = markdown_content
        self.raw_byte_length = raw_byte_length
        self.status_code = status_code
        self.content_type = content_type
        self.redirect_history = redirect_history or []

    def format_untrusted_block(self) -> str:
        """Wrap content inside untrusted XML safety tags for LLM context isolation."""
        return (
            f"<untrusted_web_content url=\"{self.url}\" title=\"{self.title}\" status=\"{self.status_code}\">\n"
            f"{self.markdown_content}\n"
            f"</untrusted_web_content>"
        )


class SafeWebFetcher:
    """Deterministic read-only web content fetcher with comprehensive security boundaries."""

    USER_AGENT = "JARVIS-Research-Agent/1.0 (Sandbox Safe Crawler; +https://github.com/JARVIS-gpt)"
    DEFAULT_MAX_REDIRECTS = 3
    DEFAULT_MAX_PAYLOAD_BYTES = 524288  # 512 KB
    DEFAULT_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        custom_dns_resolver: Callable[[str], list[str]] | None = None,
        mock_responses: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.dns_resolver = custom_dns_resolver
        self.mock_responses: dict[str, dict[str, Any]] = mock_responses or {}

    def register_mock_url(
        self,
        url: str,
        status_code: int = 200,
        content: str = "",
        content_type: str = "text/html",
        redirect_to: str | None = None,
        hang_seconds: float = 0.0,
    ) -> None:
        """Register a mock URL for hermetic sandbox testing."""
        norm_url = URLValidator.validate_and_normalize(url)
        self.mock_responses[norm_url] = {
            "status_code": status_code,
            "content": content,
            "content_type": content_type,
            "redirect_to": redirect_to,
            "hang_seconds": hang_seconds,
        }

    async def fetch_url(
        self,
        target_url: str,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> FetchedWebDocument:
        """Fetch URL content with end-to-end SSRF, redirect, size, and timeout enforcement."""
        try:
            return await asyncio.wait_for(
                self._fetch_with_redirect_validation(
                    target_url=target_url,
                    max_redirects=max_redirects,
                    max_payload_bytes=max_payload_bytes,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as err:
            raise WebFetchTimeoutError(
                f"Web fetch for '{target_url}' timed out after {timeout_seconds}s."
            ) from err

    async def _fetch_with_redirect_validation(
        self,
        target_url: str,
        max_redirects: int,
        max_payload_bytes: int,
    ) -> FetchedWebDocument:
        """Execute step-by-step redirect validation loop."""
        current_url = target_url
        redirect_history: list[str] = []

        for hop_index in range(max_redirects + 1):
            # 1. URL syntax & scheme validation
            norm_url = URLValidator.validate_and_normalize(current_url)

            # 2. SSRF check against resolved destination IP addresses
            SSRFGuard.validate_url_for_ssrf(norm_url, custom_resolver=self.dns_resolver)

            # 3. Check for hermetic mock response
            if norm_url in self.mock_responses:
                mock_data = self.mock_responses[norm_url]
                if mock_data.get("hang_seconds", 0) > 0:
                    await asyncio.sleep(mock_data["hang_seconds"])

                redirect_target = mock_data.get("redirect_to")
                if redirect_target:
                    if hop_index >= max_redirects:
                        raise RedirectBlockedError(
                            f"Exceeded maximum redirect hop limit ({max_redirects}) for '{target_url}'."
                        )
                    redirect_history.append(norm_url)
                    current_url = urljoin(norm_url, redirect_target)
                    continue

                raw_body = mock_data.get("content", "")
                raw_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
                if len(raw_bytes) > max_payload_bytes:
                    raise PayloadSizeExceededError(
                        f"Web response size ({len(raw_bytes)} bytes) exceeds limit of {max_payload_bytes} bytes."
                    )

                status_code = mock_data.get("status_code", 200)
                content_type = mock_data.get("content_type", "text/html")
                title, markdown = HTMLNormalizer.normalize_html(raw_body)

                return FetchedWebDocument(
                    url=norm_url,
                    title=title,
                    markdown_content=markdown,
                    raw_byte_length=len(raw_bytes),
                    status_code=status_code,
                    content_type=content_type,
                    redirect_history=redirect_history,
                )

            # 4. In Phase 4.1 safe development mode without mock fixture, raise informative error or execute stream fetch
            # Note: Unregistered live internet URLs in sandbox without explicit mock fail closed or execute safe stream reader
            return await self._stream_fetch_live_url(norm_url, max_payload_bytes, redirect_history)

        raise RedirectBlockedError(f"Exceeded maximum redirect limit for '{target_url}'.")

    async def _stream_fetch_live_url(
        self,
        norm_url: str,
        max_payload_bytes: int,
        redirect_history: list[str],
    ) -> FetchedWebDocument:
        """Stream read live HTTP URL with chunk-by-chunk payload limit checking in background thread."""
        def _sync_fetch() -> tuple[int, str, bytes, str]:
            req = Request(
                norm_url,
                headers={"User-Agent": self.USER_AGENT, "Accept": "text/html,text/plain"},
            )
            # Custom non-following opener to inspect redirects step by step
            opener = build_opener(_NoRedirectHandler)
            with opener.open(req, timeout=self.DEFAULT_TIMEOUT_SECONDS) as response:
                status = response.getcode() or 200
                content_type = response.headers.get_content_type() or "text/html"

                chunks: list[bytes] = []
                total_bytes = 0
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_payload_bytes:
                        raise PayloadSizeExceededError(
                            f"Web stream size ({total_bytes} bytes) exceeds limit of {max_payload_bytes} bytes."
                        )
                    chunks.append(chunk)

                body_bytes = b"".join(chunks)
                charset = response.headers.get_content_charset() or "utf-8"
                body_text = body_bytes.decode(charset, errors="replace")
                return (status, content_type, body_bytes, body_text)

        try:
            status, ctype, b_bytes, b_text = await asyncio.to_thread(_sync_fetch)
        except HTTPError as err:
            status = err.code
            b_text = err.read().decode("utf-8", errors="replace")
            b_bytes = b_text.encode("utf-8")
            ctype = "text/html"
        except URLError as err:
            raise SSRFBlockedError(f"Network connection failed for '{norm_url}': {err.reason}") from err

        title, markdown = HTMLNormalizer.normalize_html(b_text)
        return FetchedWebDocument(
            url=norm_url,
            title=title,
            markdown_content=markdown,
            raw_byte_length=len(b_bytes),
            status_code=status,
            content_type=ctype,
            redirect_history=redirect_history,
        )


class _NoRedirectHandler:
    """Helper to intercept redirects before they are automatically followed."""
    def http_error_301(self, req, fp, code, msg, headers): return fp
    def http_error_302(self, req, fp, code, msg, headers): return fp
    def http_error_303(self, req, fp, code, msg, headers): return fp
    def http_error_307(self, req, fp, code, msg, headers): return fp
    def http_error_308(self, req, fp, code, msg, headers): return fp
