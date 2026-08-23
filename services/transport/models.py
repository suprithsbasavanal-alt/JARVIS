"""Data models and exception taxonomy for external HTTP transport (Phase 9.4)."""

from dataclasses import dataclass, field
import json
from typing import Any
import urllib.parse


class TransportError(Exception):
    """Base exception for external transport failures."""
    pass


class TransportTimeoutError(TransportError):
    """Raised when an external HTTP request times out."""
    pass


class TransportRateLimitError(TransportError):
    """Raised when an external HTTP request is rate-limited (HTTP 429)."""
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TransportAuthenticationError(TransportError):
    """Raised on HTTP 401/403 authentication or authorization failures."""
    pass


class TransportUnavailableError(TransportError):
    """Raised when external network access is disabled by configuration."""
    pass


class InsecureTransportError(TransportError):
    """Raised when an insecure/cleartext HTTP URL is requested."""
    pass


class PayloadTooLargeError(TransportError):
    """Raised when request or response payload exceeds maximum configured size limits."""
    pass


@dataclass
class HttpRequest:
    """Safe HTTP request model with header sanitization and payload limits."""
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 15.0
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        # Enforce uppercase method
        self.method = self.method.upper()

        # Enforce HTTPS
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme.lower() != "https":
            raise InsecureTransportError(f"Insecure transport rejected. Scheme must be HTTPS, got: '{parsed.scheme}'.")

    def get_sanitized_headers(self) -> dict[str, str]:
        """Return headers with sensitive authorization and cookie headers redacted."""
        sanitized = {}
        for k, v in self.headers.items():
            if k.lower() in {"authorization", "x-api-key", "cookie", "set-cookie", "proxy-authorization"}:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = v
        return sanitized

    def __repr__(self) -> str:
        return f"<HttpRequest({self.method} {self.url}, headers={self.get_sanitized_headers()})>"


@dataclass
class HttpResponse:
    """Standardized HTTP response wrapper."""
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    latency_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())

    def __repr__(self) -> str:
        return f"<HttpResponse(status={self.status_code}, bytes={len(self.body)}, latency={self.latency_seconds:.3f}s)>"
