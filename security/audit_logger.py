"""Tamper-Evident Cryptographic Append-Only Audit Logger."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from core.compat import BaseModel, Field


class AuditEntry(BaseModel):
    """Immutable audit record with cryptographic hash chaining."""
    sequence_id: int
    entry_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    correlation_id: str
    actor_id: str
    event_type: str
    action_type: str
    risk_level: str
    target_resource: str
    parameters: dict[str, Any]
    decision: str
    approval_token_id: str | None = None
    prev_hash: str
    entry_hash: str = ""

    def calculate_hash(self) -> str:
        """Compute SHA-256 hash of this entry chained with previous entry hash."""
        payload = {
            "seq": self.sequence_id,
            "id": str(self.entry_id),
            "ts": self.timestamp.isoformat(),
            "session": self.session_id,
            "correlation": self.correlation_id,
            "actor": self.actor_id,
            "event_type": self.event_type,
            "action": self.action_type,
            "risk": self.risk_level,
            "target": self.target_resource,
            "params": self.parameters,
            "decision": self.decision,
            "token": self.approval_token_id,
            "prev_hash": self.prev_hash,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditLogger:
    """Tamper-evident audit log manager with hash chain verification and automated secret redaction."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
    SENSITIVE_FIELD_NAMES: tuple[str, ...] = (
        "password",
        "secret",
        "api_key",
        "token",
        "auth",
        "authorization",
        "credential",
        "private_key",
    )

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path
        self._entries: list[AuditEntry] = []
        self._last_hash = self.GENESIS_HASH

    def _sanitize_params(self, params: Any) -> Any:
        """Recursively redact sensitive parameter keys and secret substrings."""
        if isinstance(params, dict):
            sanitized: dict[str, Any] = {}
            for k, v in params.items():
                k_lower = str(k).lower()
                if any(s in k_lower for s in self.SENSITIVE_FIELD_NAMES):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self._sanitize_params(v)
            return sanitized
        if isinstance(params, list):
            return [self._sanitize_params(item) for item in params]
        return params

    def log(
        self,
        actor_id: str,
        action_type: str,
        target_resource: str,
        parameters: dict[str, Any],
        decision: str,
        session_id: str = "default_session",
        correlation_id: str = "default_correlation",
        event_type: str = "AGENT_EVENT",
        risk_level: str = "NORMAL",
        approval_token_id: str | None = None,
    ) -> AuditEntry:
        """Record an event into the audit trail with sanitized parameters."""
        seq = len(self._entries) + 1
        clean_params = self._sanitize_params(parameters)

        entry = AuditEntry(
            sequence_id=seq,
            session_id=session_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            event_type=event_type,
            action_type=action_type,
            risk_level=risk_level,
            target_resource=target_resource,
            parameters=clean_params,
            decision=decision,
            approval_token_id=approval_token_id,
            prev_hash=self._last_hash,
        )
        entry.entry_hash = entry.calculate_hash()
        self._last_hash = entry.entry_hash
        self._entries.append(entry)

        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")

        return entry

    def verify_integrity(self) -> bool:
        """Verify that the cryptographic hash chain is intact."""
        expected_prev = self.GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != expected_prev:
                return False
            if entry.entry_hash != entry.calculate_hash():
                return False
            expected_prev = entry.entry_hash
        return True

    def get_entries(self) -> list[AuditEntry]:
        """Return in-memory audit trail."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear in-memory audit trail."""
        self._entries.clear()
        self._last_hash = self.GENESIS_HASH
