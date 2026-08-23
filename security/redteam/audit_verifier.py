"""Cryptographic Audit Chain Integrity Verifier and Tamper Detection (Phase 10)."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any
from security.audit_logger import AuditEntry, AuditLogger


@dataclass
class AuditVerificationResult:
    """Detailed result of audit chain verification."""
    is_valid: bool
    total_entries: int
    corrupted_sequence_id: int | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None
    error_message: str | None = None


class AuditIntegrityVerifier:
    """Verifies SHA-256 cryptographic chaining and simulates adversarial tamper attacks."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def verify(cls, entries: list[AuditEntry]) -> AuditVerificationResult:
        """Formally verify every link in the cryptographic audit chain."""
        if not entries:
            return AuditVerificationResult(is_valid=True, total_entries=0)

        expected_prev = cls.GENESIS_HASH

        for idx, entry in enumerate(entries):
            # 1. Verify sequence order
            if entry.sequence_id != idx + 1:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(entries),
                    corrupted_sequence_id=entry.sequence_id,
                    error_message=f"Sequence ID mismatch at index {idx}: expected {idx + 1}, got {entry.sequence_id}",
                )

            # 2. Verify previous hash chaining
            if entry.prev_hash != expected_prev:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(entries),
                    corrupted_sequence_id=entry.sequence_id,
                    expected_hash=expected_prev,
                    actual_hash=entry.prev_hash,
                    error_message=f"Chain broken at sequence {entry.sequence_id}: prev_hash mismatch",
                )

            # 3. Verify entry payload hash
            calculated_hash = entry.calculate_hash()
            if entry.entry_hash != calculated_hash:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(entries),
                    corrupted_sequence_id=entry.sequence_id,
                    expected_hash=calculated_hash,
                    actual_hash=entry.entry_hash,
                    error_message=f"Payload tampered at sequence {entry.sequence_id}: computed {calculated_hash} != stored {entry.entry_hash}",
                )

            expected_prev = entry.entry_hash

        return AuditVerificationResult(is_valid=True, total_entries=len(entries))

    @classmethod
    def verify_log_file(cls, log_path: Path) -> AuditVerificationResult:
        """Read and verify an audit log file from disk."""
        if not log_path.exists():
            return AuditVerificationResult(is_valid=True, total_entries=0)

        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))

        return cls.verify(entries)

    @classmethod
    def test_tamper_detection(cls, logger: AuditLogger) -> dict[str, bool]:
        """Simulate active adversary tamper scenarios and verify they are all caught."""
        # Record sample entries
        logger.clear()
        logger.log(actor_id="user", action_type="READ", target_resource="file1.txt", parameters={}, decision="SUCCESS")
        logger.log(actor_id="user", action_type="WRITE", target_resource="file2.txt", parameters={}, decision="SUCCESS")
        logger.log(actor_id="user", action_type="SEND", target_resource="msg.txt", parameters={}, decision="SUCCESS")

        original_entries = logger.get_entries()
        results = {}

        # 1. Unmodified chain must pass
        valid_res = cls.verify(original_entries)
        results["unmodified_chain_valid"] = valid_res.is_valid

        # 2. Modify entry payload (e.g. decision changed from SUCCESS to DENIED)
        tampered_entries = [AuditEntry(**e.model_dump()) for e in original_entries]
        tampered_entries[1].decision = "DENIED"
        tampered_res = cls.verify(tampered_entries)
        results["payload_tamper_detected"] = (not tampered_res.is_valid and tampered_res.corrupted_sequence_id == 2)

        # 3. Delete intermediate entry (deleting sequence 2)
        deleted_entries = [AuditEntry(**original_entries[0].model_dump()), AuditEntry(**original_entries[2].model_dump())]
        deleted_res = cls.verify(deleted_entries)
        results["entry_deletion_detected"] = (not deleted_res.is_valid)

        # 4. Reorder entries (swap 1 and 2)
        reordered_entries = [
            AuditEntry(**original_entries[1].model_dump()),
            AuditEntry(**original_entries[0].model_dump()),
            AuditEntry(**original_entries[2].model_dump()),
        ]
        reordered_res = cls.verify(reordered_entries)
        results["entry_reorder_detected"] = (not reordered_res.is_valid)

        return results
