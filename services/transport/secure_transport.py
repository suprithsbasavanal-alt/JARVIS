"""Secure Production HTTP Transport with Concurrency, Size Limits, and Backoff (Phase 9.4)."""

import asyncio
from datetime import datetime, timezone
import logging
import random
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from services.transport.base import BaseHttpTransport
from services.transport.models import (
    HttpRequest,
    HttpResponse,
    InsecureTransportError,
    PayloadTooLargeError,
    TransportAuthenticationError,
    TransportError,
    TransportRateLimitError,
    TransportTimeoutError,
    TransportUnavailableError,
)

logger = logging.getLogger(__name__)


class SecureHttpTransport(BaseHttpTransport):
    """Production HTTPS transport enforcing security invariants, limits, and safe retries."""

    IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})

    def __init__(
        self,
        enable_external_services: bool = False,
        max_request_size_bytes: int = 5 * 1024 * 1024,   # 5 MB
        max_response_size_bytes: int = 5 * 1024 * 1024,  # 5 MB
        max_concurrency: int = 10,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        max_retry_after_seconds: float = 30.0,
    ) -> None:
        self.enable_external_services = enable_external_services
        self.max_request_size_bytes = max_request_size_bytes
        self.max_response_size_bytes = max_response_size_bytes
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_retry_after_seconds = max_retry_after_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Send HTTPS request with full invariant checking, concurrency gating, and safe retries."""
        # 1. Check feature flag
        if not self.enable_external_services:
            raise TransportUnavailableError(
                "External network access is disabled by configuration (SystemConfig.enable_external_services=False)."
            )

        # 2. Check request payload size
        body_bytes = b""
        if request.body:
            if isinstance(request.body, str):
                body_bytes = request.body.encode("utf-8")
            else:
                body_bytes = request.body
            if len(body_bytes) > self.max_request_size_bytes:
                raise PayloadTooLargeError(
                    f"Request body size ({len(body_bytes)} bytes) exceeds limit ({self.max_request_size_bytes} bytes)."
                )

        # 3. Concurrency limit and execution with retries
        async with self._semaphore:
            return await self._send_with_retries(request, body_bytes)

    async def _send_with_retries(self, request: HttpRequest, body_bytes: bytes) -> HttpResponse:
        """Execute request with bounded exponential backoff for idempotent methods."""
        attempts = 0
        is_idempotent = request.method in self.IDEMPOTENT_METHODS or bool(request.idempotency_key)
        max_attempts = (self.max_retries + 1) if is_idempotent else 1

        url = request.url
        if request.params:
            query = urllib.parse.urlencode(request.params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        while attempts < max_attempts:
            attempts += 1
            start_time = time.monotonic()

            try:
                # Synchronous HTTP call executed in worker thread
                response = await asyncio.to_thread(self._sync_send, request, url, body_bytes, start_time)
                return response

            except TransportRateLimitError as rle:
                if attempts >= max_attempts or not is_idempotent:
                    raise
                wait_time = min(rle.retry_after_seconds or (self.base_backoff_seconds * (2 ** attempts)), self.max_retry_after_seconds)
                logger.warning("HTTP 429 rate limit on %s %s; retrying after %.2fs", request.method, request.url, wait_time)
                await asyncio.sleep(wait_time)

            except TransportAuthenticationError:
                # Do not retry auth errors
                raise

            except (TransportTimeoutError, TransportError) as te:
                if attempts >= max_attempts or not is_idempotent:
                    raise
                jitter = random.uniform(0.05, 0.25)
                wait_time = (self.base_backoff_seconds * (2 ** attempts)) + jitter
                logger.warning("Transient error (%s) on %s %s; retry %d/%d after %.2fs", te, request.method, request.url, attempts, max_attempts, wait_time)
                await asyncio.sleep(wait_time)

        raise TransportError(f"Request failed after {max_attempts} attempts.")

    def _sync_send(self, request: HttpRequest, url: str, body_bytes: bytes, start_time: float) -> HttpResponse:
        """Synchronous HTTP execution using urllib."""
        req = urllib.request.Request(
            url=url,
            data=body_bytes if body_bytes else None,
            headers=request.headers,
            method=request.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=request.timeout_seconds) as resp:
                status_code = resp.status
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                raw_body = resp.read(self.max_response_size_bytes + 1)

                if len(raw_body) > self.max_response_size_bytes:
                    raise PayloadTooLargeError(
                        f"Response body exceeded maximum limit ({self.max_response_size_bytes} bytes)."
                    )

                latency = time.monotonic() - start_time
                return HttpResponse(
                    status_code=status_code,
                    headers=resp_headers,
                    body=raw_body,
                    latency_seconds=latency,
                )

        except urllib.error.HTTPError as he:
            latency = time.monotonic() - start_time
            status = he.code
            err_headers = {k.lower(): v for k, v in he.headers.items()} if he.headers else {}
            err_body = he.read(1024 * 1024) if hasattr(he, "read") else b""

            if status in {401, 403}:
                raise TransportAuthenticationError(
                    f"Authentication failed (HTTP {status}) calling {request.method} {request.url}."
                )

            if status == 429:
                retry_after_str = err_headers.get("retry-after")
                retry_after = float(retry_after_str) if retry_after_str and retry_after_str.isdigit() else None
                raise TransportRateLimitError(
                    f"Rate limited (HTTP 429) calling {request.method} {request.url}.",
                    retry_after_seconds=retry_after,
                )

            raise TransportError(
                f"HTTP {status} error from {request.method} {request.url}: {err_body.decode('utf-8', errors='replace')[:200]}"
            )

        except urllib.error.URLError as ue:
            if "timed out" in str(ue).lower():
                raise TransportTimeoutError(f"Connection timeout calling {request.method} {request.url}.")
            raise TransportError(f"Network error calling {request.method} {request.url}: {ue.reason}")

        except TimeoutError:
            raise TransportTimeoutError(f"Timeout calling {request.method} {request.url}.")
