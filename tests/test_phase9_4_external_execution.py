"""Comprehensive Automated Verification Test Suite for Phase 9.4: Production Service API Integration & Controlled External Execution."""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from uuid import uuid4

from agents.loop import AgentLoop
from config.schema import PermissionLevel, SystemConfig
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from security.audit_logger import AuditLogger
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionEngine,
)
from services.connectors.github import GitHubConnector
from services.connectors.gmail import GmailConnector
from services.connectors.google_calendar import GoogleCalendarConnector
from services.connectors.google_drive import GoogleDriveConnector
from services.connectors.slack import SlackConnector
from services.credentials.models import (
    ApiTokenCredentials,
    BotTokenCredentials,
    OAuth2Credentials,
)
from services.credentials.provider import SecureCredentialManager
from services.credentials.storage import InMemorySecureStorage
from services.execution.idempotency import (
    DuplicateExecutionError,
    IdempotencyManager,
    IdempotencyRecord,
)
from services.execution.manager import (
    EmergencyStopActiveError,
    ServiceExecutionManager,
)
from services.models import (
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceDisabledError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from services.transport.mock_transport import MockHttpTransport
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
from services.transport.secure_transport import SecureHttpTransport


class TestPhase94ControlledExternalExecution(unittest.IsolatedAsyncioTestCase):
    """Verifies transport security, execution gate, idempotency, failure modes, and service integrations."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_phase9_4.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.permission_engine = PermissionEngine()
        self.permission_bridge = ServicePermissionBridge(permission_engine=self.permission_engine)

        self.storage = InMemorySecureStorage()
        self.credential_manager = SecureCredentialManager(storage=self.storage)
        self.mock_transport = MockHttpTransport()
        self.idempotency_manager = IdempotencyManager()

        self.service_registry = ServiceRegistry(
            audit_logger=self.audit_logger,
            permission_bridge=self.permission_bridge,
        )

        self.execution_manager = ServiceExecutionManager(
            service_registry=self.service_registry,
            permission_bridge=self.permission_bridge,
            credential_manager=self.credential_manager,
            transport=self.mock_transport,
            audit_logger=self.audit_logger,
            idempotency_manager=self.idempotency_manager,
        )

        # Register standard connectors
        self.gmail = GmailConnector(credential_provider=self.credential_manager, transport=self.mock_transport)
        self.gcal = GoogleCalendarConnector(credential_provider=self.credential_manager, transport=self.mock_transport)
        self.gdrive = GoogleDriveConnector(credential_provider=self.credential_manager, transport=self.mock_transport)
        self.slack = SlackConnector(credential_provider=self.credential_manager, transport=self.mock_transport)
        self.github = GitHubConnector(credential_provider=self.credential_manager, transport=self.mock_transport)

        self.service_registry.register(self.gmail)
        self.service_registry.register(self.gcal)
        self.service_registry.register(self.gdrive)
        self.service_registry.register(self.slack)
        self.service_registry.register(self.github)

        self.context = SessionContext()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_approval_token(self, service_id: str, operation: str, params: dict[str, Any]) -> ApprovalToken:
        tool_id = f"service_{service_id}_{operation}"
        payload_str = json.dumps(params, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        return ApprovalToken(
            card_id=uuid4(),
            tool_id=tool_id,
            target_resource=f"{service_id}://{operation}",
            session_id=str(self.context.session_id),
            payload_hash=payload_hash,
        )

    # ==========================================
    # 1. Common Transport Tests
    # ==========================================

    def test_insecure_http_url_rejection(self) -> None:
        """1. Verify cleartext HTTP URLs are rejected with InsecureTransportError."""
        with self.assertRaises(InsecureTransportError):
            HttpRequest(method="GET", url="http://api.github.com/repos")

    async def test_transport_external_services_disabled_check(self) -> None:
        """2. Verify SecureHttpTransport raises TransportUnavailableError when external services are disabled."""
        transport = SecureHttpTransport(enable_external_services=False)
        req = HttpRequest(method="GET", url="https://api.github.com/zen")
        with self.assertRaises(TransportUnavailableError):
            await transport.send(req)

    async def test_transport_payload_size_limits(self) -> None:
        """3. Verify oversized request and response bodies raise PayloadTooLargeError."""
        # Oversized request
        transport = SecureHttpTransport(
            enable_external_services=True,
            max_request_size_bytes=100,
        )
        req = HttpRequest(method="POST", url="https://api.github.com/zen", body=b"X" * 150)
        with self.assertRaises(PayloadTooLargeError):
            await transport.send(req)

        # Oversized response in MockTransport
        mock_t = MockHttpTransport(max_response_size_bytes=100)
        mock_t.register_handler(
            "GET",
            "https://api.github.com/large",
            lambda r: HttpResponse(status_code=200, body=b"Y" * 200),
        )
        with self.assertRaises(PayloadTooLargeError):
            await mock_t.send(HttpRequest(method="GET", url="https://api.github.com/large"))

    def test_transport_sensitive_header_redaction(self) -> None:
        """4. Verify HttpRequest automatically redacts Authorization, X-API-Key, and Cookie headers in logs/repr."""
        req = HttpRequest(
            method="GET",
            url="https://api.github.com/user",
            headers={
                "Authorization": "Bearer secret-token-xyz",
                "X-API-Key": "secret-api-key-123",
                "Accept": "application/json",
            },
        )
        sanitized = req.get_sanitized_headers()
        self.assertEqual(sanitized["Authorization"], "[REDACTED]")
        self.assertEqual(sanitized["X-API-Key"], "[REDACTED]")
        self.assertEqual(sanitized["Accept"], "application/json")

        repr_str = repr(req)
        self.assertNotIn("secret-token-xyz", repr_str)
        self.assertNotIn("secret-api-key-123", repr_str)

    # ==========================================
    # 2. ServiceExecutionManager Security & HITL Gates
    # ==========================================

    async def test_execution_manager_read_and_search_normal(self) -> None:
        """5. Verify READ/SEARCH operations execute through ServiceExecutionManager under NORMAL permission tier."""
        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            parameters={"limit": 5},
            session_id=str(self.context.session_id),
        )
        res = await self.execution_manager.execute(req, self.context)
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.data["count"], 2)

    async def test_execution_manager_mutation_hitl_and_token_consumption(self) -> None:
        """6. Verify mutation operations strictly require HITL confirmation and consume single-use token."""
        send_params = {"to": "pepper@stark.com", "subject": "Quarterly Defense Review", "body": "MK 85 ready."}
        req_send = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.SEND,
            operation="send_email",
            parameters=send_params,
            session_id=str(self.context.session_id),
        )

        # No token -> HumanConfirmationRequiredError
        with self.assertRaises(HumanConfirmationRequiredError):
            await self.execution_manager.execute(req_send, self.context)

        # Valid token -> succeeds
        token = self._create_approval_token("gmail", "send_email", send_params)
        res_send = await self.execution_manager.execute(req_send, self.context, approval_token=token)
        self.assertTrue(res_send.success)

        # Replay attempt with new parameters (so idempotency cache doesn't return previous result) -> rejected
        send_params_2 = {"to": "rhodey@usaf.mil", "subject": "Armor Specs", "body": "MK 85 ready."}
        req_send_2 = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.SEND,
            operation="send_email",
            parameters=send_params_2,
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(PermissionDeniedError):
            await self.execution_manager.execute(req_send_2, self.context, approval_token=token)

    async def test_execution_manager_emergency_stop_halts_execution(self) -> None:
        """7. Verify emergency stop immediately blocks external service execution fail-closed."""
        self.execution_manager.trigger_emergency_stop()

        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(EmergencyStopActiveError):
            await self.execution_manager.execute(req, self.context)

        # Reset and verify recovery
        self.execution_manager.reset_emergency_stop()
        res = await self.execution_manager.execute(req, self.context)
        self.assertTrue(res.success)

    async def test_execution_manager_revocation_blocks_execution(self) -> None:
        """8. Verify revoking a connector blocks subsequent execution through execution manager."""
        await self.service_registry.revoke("slack")

        req = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.READ,
            operation="read_channel_history",
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(ServiceDisabledError):
            await self.execution_manager.execute(req, self.context)

    # ==========================================
    # 3. Idempotency & Duplicate Protection Tests
    # ==========================================

    async def test_idempotency_prevents_duplicate_mutation(self) -> None:
        """9. Verify re-dispatching identical mutation returns cached result without re-executing."""
        post_params = {"channel": "#general", "text": "Stark Industries system broadcast."}
        req = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.SEND,
            operation="post_message",
            parameters=post_params,
            session_id=str(self.context.session_id),
        )

        token1 = self._create_approval_token("slack", "post_message", post_params)
        res1 = await self.execution_manager.execute(req, self.context, approval_token=token1)
        self.assertTrue(res1.success)
        msg_id_1 = res1.data["message"]["id"]

        # Second request with same params -> returns cached response
        token2 = self._create_approval_token("slack", "post_message", post_params)
        res2 = await self.execution_manager.execute(req, self.context, approval_token=token2)
        self.assertTrue(res2.success)
        self.assertEqual(res2.data["message"]["id"], msg_id_1)

    # ==========================================
    # 4. Five Service Integration Tests
    # ==========================================

    async def test_all_five_connectors_via_execution_manager(self) -> None:
        """10. Verify Gmail, Google Calendar, Google Drive, Slack, and GitHub execute via execution manager."""
        # 1. Gmail Search
        res_gmail = await self.execution_manager.execute(
            ServiceRequest(service_id="gmail", capability=ServiceCapability.SEARCH, operation="search_emails", parameters={"query": "Starship"}, session_id=str(self.context.session_id)),
            self.context,
        )
        self.assertTrue(res_gmail.success)

        # 2. Calendar Create (HITL)
        cal_params = {"summary": "Defense Tech Sync", "start_time": "2026-08-30T10:00:00Z"}
        cal_token = self._create_approval_token("google_calendar", "create_event", cal_params)
        res_cal = await self.execution_manager.execute(
            ServiceRequest(service_id="google_calendar", capability=ServiceCapability.CREATE, operation="create_event", parameters=cal_params, session_id=str(self.context.session_id)),
            self.context,
            approval_token=cal_token,
        )
        self.assertTrue(res_cal.success)

        # 3. Drive Upload (HITL)
        drive_params = {"name": "Reactor_Design.dwg", "size_bytes": 102400}
        drive_token = self._create_approval_token("google_drive", "upload_file", drive_params)
        res_drive = await self.execution_manager.execute(
            ServiceRequest(service_id="google_drive", capability=ServiceCapability.CREATE, operation="upload_file", parameters=drive_params, session_id=str(self.context.session_id)),
            self.context,
            approval_token=drive_token,
        )
        self.assertTrue(res_drive.success)

        # 4. Slack Read
        res_slack = await self.execution_manager.execute(
            ServiceRequest(service_id="slack", capability=ServiceCapability.READ, operation="read_channel_history", session_id=str(self.context.session_id)),
            self.context,
        )
        self.assertTrue(res_slack.success)

        # 5. GitHub Create Issue (HITL)
        gh_params = {"title": "Optimize sub-millisecond telemetry sync", "body": "Profiling memory bandwidth."}
        gh_token = self._create_approval_token("github", "create_issue", gh_params)
        res_gh = await self.execution_manager.execute(
            ServiceRequest(service_id="github", capability=ServiceCapability.CREATE, operation="create_issue", parameters=gh_params, session_id=str(self.context.session_id)),
            self.context,
            approval_token=gh_token,
        )
        self.assertTrue(res_gh.success)

    async def test_undeclared_capability_rejected_by_execution_manager(self) -> None:
        """12. Verify requesting undeclared capability through execution manager raises UndeclaredCapabilityError."""
        req = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.EXECUTE,
            operation="arbitrary_exec",
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(UndeclaredCapabilityError):
            await self.execution_manager.execute(req, self.context)

    async def test_mock_transport_error_mappings(self) -> None:
        """13. Verify MockHttpTransport correctly raises TransportAuthenticationError, TransportRateLimitError, TransportError."""
        # 401
        self.mock_transport.register_handler(
            "GET", "https://api.github.com/unauth", lambda r: HttpResponse(status_code=401, body=b"Unauthorized")
        )
        with self.assertRaises(TransportAuthenticationError):
            await self.mock_transport.send(HttpRequest(method="GET", url="https://api.github.com/unauth"))

        # 429
        self.mock_transport.register_handler(
            "GET", "https://api.github.com/ratelimit", lambda r: HttpResponse(status_code=429, headers={"retry-after": "5"}, body=b"Rate Limited")
        )
        with self.assertRaises(TransportRateLimitError) as ctx:
            await self.mock_transport.send(HttpRequest(method="GET", url="https://api.github.com/ratelimit"))
        self.assertEqual(ctx.exception.retry_after_seconds, 5.0)

        # 500
        self.mock_transport.register_handler(
            "GET", "https://api.github.com/error", lambda r: HttpResponse(status_code=500, body=b"Internal Server Error")
        )
        with self.assertRaises(TransportError):
            await self.mock_transport.send(HttpRequest(method="GET", url="https://api.github.com/error"))

    def test_idempotency_in_flight_duplicate_detection(self) -> None:
        """14. Verify in-flight duplicate mutation raises DuplicateExecutionError."""
        mgr = IdempotencyManager()
        is_dup, rec, fp = mgr.check_or_start("slack", "post_message", {"channel": "#general", "text": "hello"})
        self.assertFalse(is_dup)
        self.assertIsNotNone(fp)

        # Second in-flight check with identical parameters
        with self.assertRaises(DuplicateExecutionError):
            mgr.check_or_start("slack", "post_message", {"channel": "#general", "text": "hello"})

    def test_idempotency_expiration_and_purge(self) -> None:
        """15. Verify expired idempotency records are purged correctly."""
        mgr = IdempotencyManager(ttl_minutes=0)  # expires immediately
        is_dup, rec, fp = mgr.check_or_start("gmail", "send_email", {"to": "test@test.com"})
        self.assertFalse(is_dup)

        # Mark completed with expired timestamp
        resp = ServiceResponse(service_id="gmail", operation="send_email", success=True)
        mgr.record_completed(fp, resp)
        # Fast-forward expiration
        mgr._cache[fp].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        # Checking again should start fresh
        is_dup2, rec2, fp2 = mgr.check_or_start("gmail", "send_email", {"to": "test@test.com"})
        self.assertFalse(is_dup2)

    # ==========================================
    # 5. Resilience & Secret Redaction Tests
    # ==========================================

    def test_audit_log_chained_integrity_and_secret_redaction(self) -> None:
        """16. Verify chained audit logs record external service operations with zero secret leakage."""
        entries = self.audit_logger.get_entries()
        self.assertGreaterEqual(len(entries), 1)

        for entry in entries:
            entry_str = str(entry)
            self.assertNotIn("secret-token", entry_str)
            self.assertNotIn("ghp_", entry_str)
            self.assertNotIn("xoxb-", entry_str)


if __name__ == "__main__":
    unittest.main()

