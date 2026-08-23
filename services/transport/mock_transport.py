"""Mock HTTP Transport for hermetic unit testing (Phase 9.4)."""

import asyncio
import json
import time
from typing import Any, Callable
from services.transport.base import BaseHttpTransport
from services.transport.models import (
    HttpRequest,
    HttpResponse,
    PayloadTooLargeError,
    TransportAuthenticationError,
    TransportError,
    TransportRateLimitError,
    TransportTimeoutError,
)


class MockHttpTransport(BaseHttpTransport):
    """Deterministic in-memory HTTP transport for testing API integrations."""

    def __init__(self, max_response_size_bytes: int = 5 * 1024 * 1024) -> None:
        self.max_response_size_bytes = max_response_size_bytes
        self._handlers: dict[tuple[str, str], Callable[[HttpRequest], HttpResponse]] = {}
        self.requests_sent: list[HttpRequest] = []

    def register_handler(
        self,
        method: str,
        url_prefix: str,
        handler: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        """Register a handler for a specific HTTP method and URL prefix."""
        self._handlers[(method.upper(), url_prefix)] = handler

    def register_json_response(
        self,
        method: str,
        url_prefix: str,
        status_code: int = 200,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Helper to register a static or JSON mock response."""
        body = json.dumps(data).encode("utf-8") if data is not None else b""
        resp_headers = headers or {"content-type": "application/json"}

        def handler(req: HttpRequest) -> HttpResponse:
            return HttpResponse(
                status_code=status_code,
                headers=resp_headers,
                body=body,
                latency_seconds=0.001,
            )

        self.register_handler(method, url_prefix, handler)

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Execute mock HTTP request."""
        self.requests_sent.append(request)
        start_time = time.monotonic()

        # Find matching handler
        handler = None
        for (m, prefix), h in self._handlers.items():
            if m == request.method and request.url.startswith(prefix):
                handler = h
                break

        if not handler:
            # Default 404
            return HttpResponse(
                status_code=404,
                headers={"content-type": "application/json"},
                body=b'{"error": "Not Found in MockTransport"}',
                latency_seconds=time.monotonic() - start_time,
            )

        resp = handler(request)

        # Check response size limit
        if len(resp.body) > self.max_response_size_bytes:
            raise PayloadTooLargeError(
                f"Response body exceeded maximum limit ({self.max_response_size_bytes} bytes)."
            )

        # Map error status codes to appropriate exceptions if simulating errors
        if resp.status_code in {401, 403}:
            raise TransportAuthenticationError(
                f"Authentication failed (HTTP {resp.status_code}) on {request.method} {request.url}."
            )
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "1"))
            raise TransportRateLimitError(
                f"Rate limited (HTTP 429) on {request.method} {request.url}.",
                retry_after_seconds=retry_after,
            )
        if resp.status_code >= 500:
            raise TransportError(
                f"HTTP {resp.status_code} error on {request.method} {request.url}: {resp.text()}"
            )

        return resp
