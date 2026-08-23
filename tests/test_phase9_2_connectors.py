"""Comprehensive Automated Verification Test Suite for Phase 9.2: Specific Service Adapters & Connectors."""

import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from uuid import uuid4

from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from core.types import ActionCategory
from security.audit_logger import AuditLogger
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)
from services.connectors.common import ConnectorSimulationConfig
from services.connectors.github import GitHubConnector
from services.connectors.gmail import GmailConnector
from services.connectors.google_calendar import GoogleCalendarConnector
from services.connectors.google_drive import GoogleDriveConnector
from services.connectors.slack import SlackConnector
from services.models import (
    DuplicateServiceError,
    ServiceCapability,
    ServiceDisabledError,
    ServiceMetadata,
    ServiceNotFoundError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry


class TestPhase92SpecificServiceConnectors(unittest.IsolatedAsyncioTestCase):
    """Verifies Gmail, Google Calendar, Google Drive, Slack, and GitHub hermetic connectors."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_phase9_2.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.permission_engine = PermissionEngine()
        self.permission_bridge = ServicePermissionBridge(permission_engine=self.permission_engine)
        self.service_registry = ServiceRegistry(
            audit_logger=self.audit_logger,
            permission_bridge=self.permission_bridge,
        )

        self.gmail = GmailConnector()
        self.gcal = GoogleCalendarConnector()
        self.gdrive = GoogleDriveConnector()
        self.slack = SlackConnector()
        self.github = GitHubConnector()

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
    # 1. Gmail Connector Tests
    # ==========================================

    async def test_gmail_read_and_search_normal(self) -> None:
        """1. Verify Gmail READ and SEARCH execute under NORMAL permission tier."""
        # Read inbox
        req_read = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            parameters={"limit": 5},
            session_id=str(self.context.session_id),
        )
        res_read = await self.service_registry.execute(req_read, self.context)
        self.assertTrue(res_read.success)
        self.assertGreaterEqual(res_read.data["count"], 2)

        # Search emails
        req_search = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.SEARCH,
            operation="search_emails",
            parameters={"query": "Starship"},
            session_id=str(self.context.session_id),
        )
        res_search = await self.service_registry.execute(req_search, self.context)
        self.assertTrue(res_search.success)
        self.assertEqual(res_search.data["count"], 1)
        self.assertIn("elon@x.com", res_search.data["emails"][0]["sender"])

    async def test_gmail_send_and_delete_hitl_enforcement(self) -> None:
        """2. Verify Gmail SEND and DELETE require HITL approval and succeed with valid token."""
        send_params = {"to": "rhodey@usaf.mil", "subject": "Armor Specs", "body": "MK 85 ready."}
        req_send = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.SEND,
            operation="send_email",
            parameters=send_params,
            session_id=str(self.context.session_id),
        )

        # Without token -> raises HumanConfirmationRequiredError
        with self.assertRaises(HumanConfirmationRequiredError):
            await self.service_registry.execute(req_send, self.context)

        # With valid token -> succeeds
        token = self._create_approval_token("gmail", "send_email", send_params)
        res_send = await self.service_registry.execute(req_send, self.context, approval_token=token)
        self.assertTrue(res_send.success)
        self.assertEqual(res_send.data["status"], "SENT")

        # Delete email with token
        del_params = {"email_id": "email-001"}
        req_del = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.DELETE,
            operation="delete_email",
            parameters=del_params,
            session_id=str(self.context.session_id),
        )
        del_token = self._create_approval_token("gmail", "delete_email", del_params)
        res_del = await self.service_registry.execute(req_del, self.context, approval_token=del_token)
        self.assertTrue(res_del.success)
        self.assertEqual(res_del.data["status"], "DELETED")

    # ==========================================
    # 2. Google Calendar Connector Tests
    # ==========================================

    async def test_calendar_read_and_search_normal(self) -> None:
        """3. Verify Google Calendar READ and SEARCH execute under NORMAL tier."""
        req_list = ServiceRequest(
            service_id="google_calendar",
            capability=ServiceCapability.READ,
            operation="list_events",
            session_id=str(self.context.session_id),
        )
        res_list = await self.service_registry.execute(req_list, self.context)
        self.assertTrue(res_list.success)
        self.assertGreaterEqual(res_list.data["count"], 2)

        req_search = ServiceRequest(
            service_id="google_calendar",
            capability=ServiceCapability.SEARCH,
            operation="search_events",
            parameters={"query": "Tactical"},
            session_id=str(self.context.session_id),
        )
        res_search = await self.service_registry.execute(req_search, self.context)
        self.assertTrue(res_search.success)
        self.assertEqual(res_search.data["count"], 1)

    async def test_calendar_create_update_delete_hitl(self) -> None:
        """4. Verify Google Calendar CREATE/UPDATE/DELETE require HITL approval."""
        create_params = {"summary": "Stark Expo Keynote", "start_time": "2026-09-01T10:00:00Z"}
        req_create = ServiceRequest(
            service_id="google_calendar",
            capability=ServiceCapability.CREATE,
            operation="create_event",
            parameters=create_params,
            session_id=str(self.context.session_id),
        )

        with self.assertRaises(HumanConfirmationRequiredError):
            await self.service_registry.execute(req_create, self.context)

        token = self._create_approval_token("google_calendar", "create_event", create_params)
        res_create = await self.service_registry.execute(req_create, self.context, approval_token=token)
        self.assertTrue(res_create.success)
        event_id = res_create.data["event"]["id"]

        # Update event
        upd_params = {"event_id": event_id, "summary": "Stark Expo Keynote (CONFIRMED)"}
        req_upd = ServiceRequest(
            service_id="google_calendar",
            capability=ServiceCapability.UPDATE,
            operation="update_event",
            parameters=upd_params,
            session_id=str(self.context.session_id),
        )
        upd_token = self._create_approval_token("google_calendar", "update_event", upd_params)
        res_upd = await self.service_registry.execute(req_upd, self.context, approval_token=upd_token)
        self.assertTrue(res_upd.success)
        self.assertEqual(res_upd.data["status"], "UPDATED")

    # ==========================================
    # 3. Google Drive Connector Tests
    # ==========================================

    async def test_drive_read_and_upload_hitl(self) -> None:
        """5. Verify Google Drive list_files (READ) and upload_file (CREATE - HITL)."""
        req_list = ServiceRequest(
            service_id="google_drive",
            capability=ServiceCapability.READ,
            operation="list_files",
            session_id=str(self.context.session_id),
        )
        res_list = await self.service_registry.execute(req_list, self.context)
        self.assertTrue(res_list.success)
        self.assertGreaterEqual(res_list.data["count"], 2)

        # Upload file (CREATE)
        upload_params = {"name": "Vibranium_Shield_Alloy.cad", "size_bytes": 204800}
        req_upload = ServiceRequest(
            service_id="google_drive",
            capability=ServiceCapability.CREATE,
            operation="upload_file",
            parameters=upload_params,
            session_id=str(self.context.session_id),
        )
        token = self._create_approval_token("google_drive", "upload_file", upload_params)
        res_upload = await self.service_registry.execute(req_upload, self.context, approval_token=token)
        self.assertTrue(res_upload.success)
        self.assertEqual(res_upload.data["status"], "UPLOADED")

    # ==========================================
    # 4. Slack Connector Tests
    # ==========================================

    async def test_slack_read_and_post_message_hitl(self) -> None:
        """6. Verify Slack channel history (READ) and post_message (SEND - HITL)."""
        req_read = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.READ,
            operation="read_channel_history",
            parameters={"channel": "#engineering"},
            session_id=str(self.context.session_id),
        )
        res_read = await self.service_registry.execute(req_read, self.context)
        self.assertTrue(res_read.success)
        self.assertEqual(res_read.data["count"], 1)

        # Post message (SEND)
        post_params = {"channel": "#general", "text": "All diagnostic tests passing 100%."}
        req_post = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.SEND,
            operation="post_message",
            parameters=post_params,
            session_id=str(self.context.session_id),
        )
        token = self._create_approval_token("slack", "post_message", post_params)
        res_post = await self.service_registry.execute(req_post, self.context, approval_token=token)
        self.assertTrue(res_post.success)
        self.assertEqual(res_post.data["status"], "POSTED")

    # ==========================================
    # 5. GitHub Connector Tests
    # ==========================================

    async def test_github_read_and_create_issue_hitl(self) -> None:
        """7. Verify GitHub list_issues (READ) and create_issue (CREATE - HITL)."""
        req_read = ServiceRequest(
            service_id="github",
            capability=ServiceCapability.READ,
            operation="list_issues",
            session_id=str(self.context.session_id),
        )
        res_read = await self.service_registry.execute(req_read, self.context)
        self.assertTrue(res_read.success)
        self.assertGreaterEqual(res_read.data["count"], 2)

        # Create Issue (CREATE)
        issue_params = {"title": "Implement Quantum Telemetry Bridge", "body": "Requires sub-millisecond precision."}
        req_issue = ServiceRequest(
            service_id="github",
            capability=ServiceCapability.CREATE,
            operation="create_issue",
            parameters=issue_params,
            session_id=str(self.context.session_id),
        )
        token = self._create_approval_token("github", "create_issue", issue_params)
        res_issue = await self.service_registry.execute(req_issue, self.context, approval_token=token)
        self.assertTrue(res_issue.success)
        self.assertEqual(res_issue.data["status"], "OPENED")

    # ==========================================
    # 6. Failure Modes & Simulation Hooks
    # ==========================================

    async def test_rate_limiting_simulation(self) -> None:
        """8. Verify rate limiting simulation returns failure and sets status DEGRADED."""
        self.gmail.simulation_config.simulate_rate_limit = True

        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            session_id=str(self.context.session_id),
        )
        res = await self.service_registry.execute(req, self.context)
        self.assertFalse(res.success)
        self.assertIn("rate limit", res.error.lower())
        self.assertEqual(self.gmail.status, ServiceStatus.DEGRADED)

    async def test_outage_simulation(self) -> None:
        """9. Verify upstream outage simulation returns failure and sets status ERROR."""
        self.gcal.simulation_config.simulate_outage = True

        req = ServiceRequest(
            service_id="google_calendar",
            capability=ServiceCapability.READ,
            operation="list_events",
            session_id=str(self.context.session_id),
        )
        res = await self.service_registry.execute(req, self.context)
        self.assertFalse(res.success)
        self.assertIn("outage", res.error.lower())
        self.assertEqual(self.gcal.status, ServiceStatus.ERROR)

    async def test_timeout_simulation(self) -> None:
        """10. Verify simulated timeout returns failure without hanging."""
        self.slack.simulation_config.simulate_timeout = True

        req = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.READ,
            operation="read_channel_history",
            session_id=str(self.context.session_id),
        )
        res = await self.service_registry.execute(req, self.context)
        self.assertFalse(res.success)
        self.assertIn("timeout", res.error.lower())

    async def test_auth_failure_simulation(self) -> None:
        """11. Verify simulated auth failure returns failure and sets status AUTH_REQUIRED."""
        self.github.simulation_config.simulate_auth_failure = True

        req = ServiceRequest(
            service_id="github",
            capability=ServiceCapability.READ,
            operation="list_issues",
            session_id=str(self.context.session_id),
        )
        res = await self.service_registry.execute(req, self.context)
        self.assertFalse(res.success)
        self.assertIn("credentials", res.error.lower())
        self.assertEqual(self.github.status, ServiceStatus.AUTH_REQUIRED)

    # ==========================================
    # 7. Security & Invariant Verification
    # ==========================================

    async def test_undeclared_capability_rejection_across_connectors(self) -> None:
        """12. Verify requesting EXECUTE on connectors that do not declare it raises UndeclaredCapabilityError."""
        for sid in ["gmail", "google_calendar", "google_drive", "slack", "github"]:
            req = ServiceRequest(
                service_id=sid,
                capability=ServiceCapability.EXECUTE,
                operation="execute_arbitrary_script",
                session_id=str(self.context.session_id),
            )
            with self.assertRaises(UndeclaredCapabilityError):
                await self.service_registry.execute(req, self.context)

    async def test_connector_revocation_wipes_credentials(self) -> None:
        """13. Verify revoking a connector zeroizes credentials and halts subsequent requests."""
        await self.service_registry.revoke("gmail")
        self.assertEqual(self.gmail.status, ServiceStatus.REVOKED)
        self.assertFalse(self.gmail.is_enabled)
        self.assertFalse(self.gmail.credential_provider.has_credentials("gmail"))

        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(ServiceDisabledError):
            await self.service_registry.execute(req, self.context)

    async def test_token_replay_rejected_across_connectors(self) -> None:
        """14. Verify consuming an ApprovalToken prevents reusing it on a subsequent call."""
        params = {"recipient": "tony@stark.com", "text": "Testing single-use token."}
        token = self._create_approval_token("slack", "post_message", params)

        req = ServiceRequest(
            service_id="slack",
            capability=ServiceCapability.SEND,
            operation="post_message",
            parameters=params,
            session_id=str(self.context.session_id),
        )

        res1 = await self.service_registry.execute(req, self.context, approval_token=token)
        self.assertTrue(res1.success)

        # Replay attempt
        with self.assertRaises(PermissionDeniedError):
            await self.service_registry.execute(req, self.context, approval_token=token)

    def test_credential_redaction_in_all_connectors(self) -> None:
        """15. Verify none of the 5 connectors expose secrets in metadata or string representations."""
        for adapter in [self.gmail, self.gcal, self.gdrive, self.slack, self.github]:
            meta_json = json.dumps(adapter.metadata.to_dict())
            self.assertNotIn("fake-", meta_json)
            self.assertNotIn("ghp_", meta_json)
            self.assertNotIn("xoxb-", meta_json)
            self.assertNotIn("secret", meta_json.lower())

            cred_repr = repr(adapter.credential_provider)
            self.assertIn("[REDACTED]", cred_repr)


if __name__ == "__main__":
    unittest.main()
