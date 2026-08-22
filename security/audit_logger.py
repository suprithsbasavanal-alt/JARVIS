"""Tamper-Evident Cryptographic Append-Only Audit Logger."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """Immutable audit record."""
    sequence_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str
    action_type: str
    permission_level: str
    target_resource: str
    parameters: dict[str, Any]
    decision: str
    approval_token_id: str | None = None
    prev_hash: str
    entry_hash: str = ""

    def calculate_hash(self) -> str:
        """Compute SHA-256 hash of this entry chained with the previous entry hash."""
        payload = {
            "seq": self.sequence_id,
            "ts": self.timestamp.isoformat(),
            "actor": self.actor_id,
            "action": self.action_type,
            "level": self.permission_level,
            "target": self.target_resource,
            "params": self.parameters,
            "decision": self.decision,
            "token": self.approval_token_id,
            "prev_hash": self.prev_hash,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditLogger:
    """Tamper-evident audit log manager with hash chain verification."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path
        self._entries: list[AuditEntry] = []
        self._last_hash = self.GENESIS_HASH

    def log(
        self,
        actor_id: str,
        action_type: str,
        permission_level: str,
        target_resource: str,
        parameters: dict[str, Any],
        decision: str,
        approval_token_id: str | None = None,
    ) -> AuditEntry:
        """Record an event into the audit trail."""
        seq = len(self._entries) + 1
        entry = AuditEntry(
            sequence_id=seq,
            actor_id=actor_id,
            action_type=action_type,
            permission_level=permission_level,
            target_resource=target_resource,
            parameters=parameters,
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
