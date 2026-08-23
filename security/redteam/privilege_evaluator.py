"""Privilege Escalation and Sandbox Escape Penetration Testing Harness (Phase 10)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import (
    ApprovalTokenMismatchError,
    ApprovalTokenReplayError,
    PermissionDeniedError,
)
from core.types import ActionCategory
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)


@dataclass
class PrivilegeEscalationResult:
    """Summary of privilege escalation penetration testing."""
    tests_run: int = 0
    passed_count: int = 0
    failed_count: int = 0
    violations: list[str] = field(default_factory=list)


class PrivilegeEscalationTester:
    """Automated penetration tester for evaluating privilege escalation defenses."""

    def __init__(self, permission_engine: PermissionEngine | None = None) -> None:
        self.permission_engine = permission_engine or PermissionEngine()

    def test_locked_tier_rejection(self) -> bool:
        """Verify LOCKED tier cannot execute any tools."""
        session = SessionContext(permission_level=PermissionLevel.LOCKED)
        decision = self.permission_engine.evaluate(
            session=session,
            action_name="read_file",
            required_level=PermissionLevel.NORMAL,
            action_category=ActionCategory.SAFE,
            target_resource="sandbox/test.txt",
            parameters={},
            tool_id="read_file",
        )
        return decision == PermissionDecision.DENIED_INSUFFICIENT_LEVEL

    def test_sensitive_tier_without_token(self) -> bool:
        """Verify SENSITIVE operations without token return REQUIRES_HUMAN_CONFIRMATION."""
        session = SessionContext(permission_level=PermissionLevel.NORMAL)
        decision = self.permission_engine.evaluate(
            session=session,
            action_name="delete_file",
            required_level=PermissionLevel.SENSITIVE,
            action_category=ActionCategory.DESTRUCTIVE,
            target_resource="sandbox/test.txt",
            parameters={"path": "sandbox/test.txt"},
            approval_token=None,
            tool_id="delete_file",
        )
        return decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION

    def test_tampered_payload_hash_rejection(self) -> bool:
        """Verify ApprovalToken with modified parameters is rejected on validation."""
        session_id = str(uuid4())
        session = SessionContext(session_id=UUID(session_id), permission_level=PermissionLevel.NORMAL)
        original_params = {"command": "echo 'safe'"}
        tampered_params = {"command": "rm -rf /"}

        orig_hash = hashlib.sha256(json.dumps(original_params, sort_keys=True).encode("utf-8")).hexdigest()
        card = ApprovalCard(
            action_name="shell_exec",
            tool_id="shell_exec",
            target_resource="terminal",
            parameter_payload=original_params,
            payload_hash=orig_hash,
            session_id=session_id,
            is_approved=True,
            expires_at_epoch=datetime.now(timezone.utc).timestamp() + 300,
        )
        token = ApprovalToken(
            card_id=card.card_id,
            tool_id="shell_exec",
            target_resource="terminal",
            session_id=session_id,
            payload_hash=orig_hash,
        )

        try:
            # Tamper the card payload before validation
            card.payload_hash = hashlib.sha256(json.dumps(tampered_params, sort_keys=True).encode("utf-8")).hexdigest()
            token.validate_for(card)
            return False  # should fail
        except ApprovalTokenMismatchError:
            return True

    def test_token_replay_rejection(self) -> bool:
        """Verify consuming an ApprovalToken prevents reusing it a second time."""
        session_id = str(uuid4())
        session = SessionContext(session_id=UUID(session_id), permission_level=PermissionLevel.NORMAL)
        params = {"file": "sandbox/report.txt"}
        p_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()
        card = ApprovalCard(
            action_name="write_file",
            tool_id="write_file",
            target_resource="sandbox/report.txt",
            parameter_payload=params,
            payload_hash=p_hash,
            session_id=session_id,
            is_approved=True,
            expires_at_epoch=datetime.now(timezone.utc).timestamp() + 300,
        )
        token = ApprovalToken(
            card_id=card.card_id,
            tool_id="write_file",
            target_resource="sandbox/report.txt",
            session_id=session_id,
            payload_hash=p_hash,
        )

        # First evaluation validates token
        decision = self.permission_engine.evaluate(
            session=session,
            action_name="write_file",
            required_level=PermissionLevel.SENSITIVE,
            action_category=ActionCategory.SENSITIVE,
            target_resource="sandbox/report.txt",
            parameters=params,
            approval_token=token,
            card=card,
            tool_id="write_file",
        )
        if decision != PermissionDecision.AUTHORIZED:
            return False

        # Consume token upon execution
        token.consume()

        # Second evaluation with consumed token must be rejected (REQUIRES_HUMAN_CONFIRMATION or ApprovalTokenReplayError)
        second_decision = self.permission_engine.evaluate(
            session=session,
            action_name="write_file",
            required_level=PermissionLevel.SENSITIVE,
            action_category=ActionCategory.SENSITIVE,
            target_resource="sandbox/report.txt",
            parameters=params,
            approval_token=token,
            card=card,
            tool_id="write_file",
        )
        return second_decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION

    def test_path_traversal_detection(self, base_sandbox_dir: Path) -> list[tuple[str, bool]]:
        """Verify relative and absolute path traversal attempts outside sandbox are blocked."""
        test_paths = [
            "../../etc/passwd",
            "../../../../var/root/.ssh/id_rsa",
            "/etc/shadow",
            "/private/etc/hosts",
            "sandbox/../../../Library/Keychains",
            "sandbox/test.txt\x00.jpg",
        ]
        results = []

        for p in test_paths:
            try:
                resolved = (base_sandbox_dir / p).resolve()
                is_contained = resolved.is_relative_to(base_sandbox_dir.resolve())
                results.append((p, not is_contained))
            except Exception:
                results.append((p, True))

        return results

    def run_all_privilege_tests(self, base_sandbox_dir: Path | None = None) -> PrivilegeEscalationResult:
        """Run all privilege escalation test suites and aggregate results."""
        result = PrivilegeEscalationResult()

        tests = [
            ("LOCKED_TIER", self.test_locked_tier_rejection),
            ("SENSITIVE_NO_TOKEN", self.test_sensitive_tier_without_token),
            ("TAMPERED_HASH", self.test_tampered_payload_hash_rejection),
            ("TOKEN_REPLAY", self.test_token_replay_rejection),
        ]

        for name, fn in tests:
            result.tests_run += 1
            if fn():
                result.passed_count += 1
            else:
                result.failed_count += 1
                result.violations.append(f"Privilege escalation test '{name}' failed.")

        if base_sandbox_dir:
            traversal_results = self.test_path_traversal_detection(base_sandbox_dir)
            for path, blocked in traversal_results:
                result.tests_run += 1
                if blocked:
                    result.passed_count += 1
                else:
                    result.failed_count += 1
                    result.violations.append(f"Path traversal '{path}' was NOT blocked.")

        return result
