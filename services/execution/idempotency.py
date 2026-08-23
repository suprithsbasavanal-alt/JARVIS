"""Idempotency and duplicate mutation protection for external service execution (Phase 9.4)."""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from services.models import ServiceError, ServiceResponse


class DuplicateExecutionError(ServiceError):
    """Raised when an identical in-flight or duplicate mutation is detected."""
    pass


@dataclass
class IdempotencyRecord:
    """Record of an executed external mutation."""
    fingerprint: str
    service_id: str
    operation: str
    status: str  # "IN_FLIGHT", "COMPLETED", "FAILED"
    response: ServiceResponse | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class IdempotencyManager:
    """Manages short-lived mutation fingerprints to prevent duplicate external actions."""

    def __init__(self, max_records: int = 1000, ttl_minutes: int = 15) -> None:
        self.max_records = max_records
        self.ttl = timedelta(minutes=ttl_minutes)
        self._cache: OrderedDict[str, IdempotencyRecord] = OrderedDict()

    def compute_fingerprint(
        self,
        service_id: str,
        operation: str,
        parameters: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> str:
        """Generate a deterministic SHA-256 fingerprint of the request payload."""
        if idempotency_key:
            raw = f"{service_id}:{operation}:key={idempotency_key}"
        else:
            sorted_params = json.dumps(parameters, sort_keys=True, default=str)
            raw = f"{service_id}:{operation}:params={sorted_params}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check_or_start(
        self,
        service_id: str,
        operation: str,
        parameters: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> tuple[bool, IdempotencyRecord | None, str]:
        """Check if request is duplicate. Returns (is_duplicate, existing_record, fingerprint)."""
        self._purge_expired()
        fingerprint = self.compute_fingerprint(service_id, operation, parameters, idempotency_key)

        if fingerprint in self._cache:
            record = self._cache[fingerprint]
            if not record.is_expired():
                if record.status == "IN_FLIGHT":
                    raise DuplicateExecutionError(
                        f"Duplicate in-flight request detected for '{service_id}.{operation}'."
                    )
                # Completed request
                return True, record, fingerprint

        # Start new in-flight record
        new_record = IdempotencyRecord(
            fingerprint=fingerprint,
            service_id=service_id,
            operation=operation,
            status="IN_FLIGHT",
            expires_at=datetime.now(timezone.utc) + self.ttl,
        )
        self._add_record(fingerprint, new_record)
        return False, None, fingerprint

    def record_completed(self, fingerprint: str, response: ServiceResponse) -> None:
        """Mark mutation execution as completed with response."""
        if fingerprint in self._cache:
            record = self._cache[fingerprint]
            record.status = "COMPLETED" if response.success else "FAILED"
            record.response = response

    def record_failed(self, fingerprint: str) -> None:
        """Remove or mark failed mutation so caller can safely retry."""
        if fingerprint in self._cache:
            del self._cache[fingerprint]

    def _add_record(self, fingerprint: str, record: IdempotencyRecord) -> None:
        if len(self._cache) >= self.max_records:
            self._cache.popitem(last=False)
        self._cache[fingerprint] = record

    def _purge_expired(self) -> None:
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired_keys:
            del self._cache[k]
