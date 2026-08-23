"""Comprehensive Automated Verification Test Suite for Phase 9.3: Real Service Authentication & Secure Credential Management."""

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
from core.ipc_server import IPCServer
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
from services.credentials.adapters import (
    GitHubAuthAdapter,
    GmailAuthAdapter,
    GoogleCalendarAuthAdapter,
    GoogleDriveAuthAdapter,
    SlackAuthAdapter,
)
from services.credentials.models import (
    ApiTokenCredentials,
    BaseCredential,
    BotTokenCredentials,
    CredentialType,
    GenericServiceCredentials,
    OAuth2Credentials,
)
from services.credentials.oauth import (
    OAuth2LifecycleManager,
    OAuthRefreshError,
    OAuthState,
    OAuthStateError,
)
from services.credentials.provider import SecureCredentialManager
from services.credentials.storage import (
    InMemorySecureStorage,
    KeychainSecureStorage,
)
from services.models import (
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceDisabledError,
    ServiceRequest,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry


class TestPhase93AuthenticationAndCredentials(unittest.IsolatedAsyncioTestCase):
    """Verifies secure credential storage, OAuth2 lifecycle, service adapters, rotation, and non-disclosure."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_phase9_3.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.permission_engine = PermissionEngine()
        self.permission_bridge = ServicePermissionBridge(permission_engine=self.permission_engine)

        self.storage = InMemorySecureStorage()
        self.credential_manager = SecureCredentialManager(storage=self.storage)
        self.oauth_manager = OAuth2LifecycleManager(credential_manager=self.credential_manager)

        self.service_registry = ServiceRegistry(
            audit_logger=self.audit_logger,
            permission_bridge=self.permission_bridge,
        )

        self.context = SessionContext()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    # ==========================================
    # 1. Storage & Credential Model Tests
    # ==========================================

    def test_in_memory_and_keychain_storage(self) -> None:
        """1. Verify InMemorySecureStorage and KeychainSecureStorage handle store, get, delete, wipe."""
        # InMemory
        in_mem = InMemorySecureStorage()
        cred = ApiTokenCredentials(service_id="github", token="ghp_test_token_12345")
        in_mem.store(cred)
        self.assertTrue(in_mem.has_credential("github"))
        self.assertEqual(in_mem.get("github").token, "ghp_test_token_12345")
        in_mem.delete("github")
        self.assertFalse(in_mem.has_credential("github"))

        # Keychain with test fallback
        keychain = KeychainSecureStorage(allow_in_memory_fallback=True)
        keychain.store(cred)
        self.assertTrue(keychain.has_credential("github"))
        self.assertEqual(keychain.get("github").token, "ghp_test_token_12345")
        keychain.wipe_all()
        self.assertFalse(keychain.has_credential("github"))

    def test_credential_models_redaction_and_expiry(self) -> None:
        """2. Verify typed credential models never expose secrets in repr, str, or to_safe_dict."""
        now = datetime.now(timezone.utc)
        oauth = OAuth2Credentials(
            service_id="gmail",
            access_token="secret-access-token-999",
            refresh_token="secret-refresh-token-888",
            expires_at=now + timedelta(seconds=30),  # within 60s buffer -> expired
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        self.assertTrue(oauth.is_expired(buffer_seconds=60))
        safe_dict = oauth.to_safe_dict()
        self.assertNotIn("secret-access-token", json.dumps(safe_dict))
        self.assertNotIn("secret-refresh-token", json.dumps(safe_dict))
        self.assertTrue(safe_dict["has_refresh_token"])

        repr_str = repr(oauth)
        self.assertIn("[REDACTED]", repr_str)
        self.assertNotIn("secret-access-token", repr_str)

    # ==========================================
    # 2. SecureCredentialManager Operations
    # ==========================================

    def test_credential_manager_rotation_and_revocation(self) -> None:
        """3. Verify SecureCredentialManager handles typed storage, rotation, and revocation."""
        bot_cred = BotTokenCredentials(service_id="slack", bot_token="xoxb-initial-token-111")
        self.credential_manager.store_typed_credential(bot_cred)

        self.assertTrue(self.credential_manager.has_credentials("slack"))
        self.assertEqual(self.credential_manager.get_credential("slack", "bot_token"), "xoxb-initial-token-111")

        # Rotate
        new_bot_cred = BotTokenCredentials(service_id="slack", bot_token="xoxb-rotated-token-222")
        self.credential_manager.rotate_typed_credential(new_bot_cred)
        self.assertEqual(self.credential_manager.get_credential("slack", "bot_token"), "xoxb-rotated-token-222")

        # Safe metadata query
        meta = self.credential_manager.get_credential_metadata("slack")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["credential_type"], CredentialType.BOT_TOKEN.value)
        self.assertNotIn("xoxb-", json.dumps(meta))

        # Revoke
        self.credential_manager.revoke_credentials("slack")
        self.assertFalse(self.credential_manager.has_credentials("slack"))
        self.assertIsNone(self.credential_manager.get_credential("slack", "bot_token"))

    # ==========================================
    # 3. OAuth2 Lifecycle & CSRF Security
    # ==========================================

    def test_oauth_authorization_url_and_csrf_state(self) -> None:
        """4. Verify OAuth2 authorization URL generation and single-use CSRF state validation."""
        auth_url, state = self.oauth_manager.generate_authorization_url(
            service_id="gmail",
            client_id="test-client-id-123",
            redirect_uri="http://127.0.0.1:8080/callback",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            auth_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        )

        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", auth_url)
        self.assertIn("client_id=test-client-id-123", auth_url)
        self.assertIn(f"state={state}", auth_url)

        # First validation -> succeeds and consumes
        valid = self.oauth_manager.validate_callback_state("gmail", state)
        self.assertTrue(valid)

        # Replay attempt -> rejected
        replay_valid = self.oauth_manager.validate_callback_state("gmail", state)
        self.assertFalse(replay_valid)

    def test_oauth_state_expiration_and_mismatch(self) -> None:
        """5. Verify expired state and cross-service state mismatch are rejected."""
        # Expired state
        state_token = "expired-state-token"
        expired_state = OAuthState(
            token=state_token,
            service_id="gmail",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        self.oauth_manager._states[state_token] = expired_state

        self.assertFalse(self.oauth_manager.validate_callback_state("gmail", state_token))

        # Service mismatch
        _, valid_state = self.oauth_manager.generate_authorization_url(
            service_id="gmail",
            client_id="cid",
            redirect_uri="uri",
            scopes=[],
            auth_endpoint="http://example.com",
        )
        self.assertFalse(self.oauth_manager.validate_callback_state("google_calendar", valid_state))

    def test_oauth_code_exchange_and_token_refresh(self) -> None:
        """6. Verify OAuth2 authorization code exchange and token refresh lifecycle."""
        _, state = self.oauth_manager.generate_authorization_url(
            service_id="google_calendar",
            client_id="test-cal-client",
            redirect_uri="http://127.0.0.1:8080/callback",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            auth_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        )

        # Exchange code
        creds = self.oauth_manager.exchange_code_for_token(
            service_id="google_calendar",
            code="auth-code-xyz",
            state_token=state,
            client_id="test-cal-client",
            client_secret="test-cal-secret",
            token_endpoint="https://oauth2.googleapis.com/token",
            mock_token_response={
                "access_token": "mock-access-token-001",
                "refresh_token": "mock-refresh-token-001",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.readonly",
            },
        )

        self.assertEqual(creds.access_token, "mock-access-token-001")
        self.assertTrue(self.credential_manager.has_credentials("google_calendar"))

        # Refresh token
        refreshed = self.oauth_manager.refresh_access_token(
            service_id="google_calendar",
            client_id="test-cal-client",
            client_secret="test-cal-secret",
            token_endpoint="https://oauth2.googleapis.com/token",
            mock_refresh_response={
                "access_token": "mock-access-token-refreshed-002",
                "expires_in": 7200,
            },
        )
        self.assertEqual(refreshed.access_token, "mock-access-token-refreshed-002")
        self.assertEqual(
            self.credential_manager.get_credential("google_calendar", "access_token"),
            "mock-access-token-refreshed-002",
        )

    def test_oauth_refresh_failure_isolation(self) -> None:
        """7. Verify simulated OAuth refresh failure raises OAuthRefreshError."""
        # No credentials stored -> refresh raises OAuthRefreshError
        with self.assertRaises(OAuthRefreshError):
            self.oauth_manager.refresh_access_token(
                service_id="google_drive",
                client_id="test-client",
                client_secret="test-secret",
                token_endpoint="https://oauth2.googleapis.com/token",
            )

    # ==========================================
    # 4. Service-Specific Auth Adapters
    # ==========================================

    def test_service_specific_auth_adapters(self) -> None:
        """8. Verify Gmail, Google Calendar, Google Drive, Slack, and GitHub auth adapters."""
        # Gmail Auth Adapter
        gmail_auth = GmailAuthAdapter(self.oauth_manager)
        _, state_gmail = gmail_auth.get_auth_url("client-gmail", "http://127.0.0.1:8080/callback")
        gmail_creds = gmail_auth.authenticate_code("code-gmail", state_gmail, "client-gmail", "secret-gmail")
        self.assertTrue(self.credential_manager.has_credentials("gmail"))
        self.assertEqual(gmail_creds.service_id, "gmail")

        # Google Calendar Auth Adapter
        cal_auth = GoogleCalendarAuthAdapter(self.oauth_manager)
        _, state_cal = cal_auth.get_auth_url("client-cal", "http://127.0.0.1:8080/callback")
        cal_creds = cal_auth.authenticate_code("code-cal", state_cal, "client-cal", "secret-cal")
        self.assertTrue(self.credential_manager.has_credentials("google_calendar"))

        # Google Drive Auth Adapter
        drive_auth = GoogleDriveAuthAdapter(self.oauth_manager)
        _, state_drive = drive_auth.get_auth_url("client-drive", "http://127.0.0.1:8080/callback")
        drive_creds = drive_auth.authenticate_code("code-drive", state_drive, "client-drive", "secret-drive")
        self.assertTrue(self.credential_manager.has_credentials("google_drive"))

        # Slack Auth Adapter
        slack_auth = SlackAuthAdapter(self.credential_manager)
        slack_creds = slack_auth.authenticate_bot_token("xoxb-test-bot-token-999", team_id="T012345")
        self.assertTrue(self.credential_manager.has_credentials("slack"))
        self.assertEqual(slack_creds.bot_token, "xoxb-test-bot-token-999")

        # Empty Slack bot token -> raises ServiceAuthenticationError
        with self.assertRaises(ServiceAuthenticationError):
            slack_auth.authenticate_bot_token("")

        # GitHub Auth Adapter
        github_auth = GitHubAuthAdapter(self.credential_manager)
        gh_creds = github_auth.authenticate_pat("ghp_test_pat_token_999", username="suprith")
        self.assertTrue(self.credential_manager.has_credentials("github"))
        self.assertEqual(gh_creds.token, "ghp_test_pat_token_999")

        # Empty GitHub PAT -> raises ServiceAuthenticationError
        with self.assertRaises(ServiceAuthenticationError):
            github_auth.authenticate_pat("   ")

    # ==========================================
    # 5. Connector Integration with SecureCredentialManager
    # ==========================================

    async def test_connectors_with_secure_credential_manager(self) -> None:
        """9. Verify all 5 connectors execute successfully when backed by SecureCredentialManager."""
        # Setup credentials in manager
        self.credential_manager.store_typed_credential(
            OAuth2Credentials(service_id="gmail", access_token="mock-gmail-token")
        )
        self.credential_manager.store_typed_credential(
            OAuth2Credentials(service_id="google_calendar", access_token="mock-gcal-token")
        )
        self.credential_manager.store_typed_credential(
            OAuth2Credentials(service_id="google_drive", access_token="mock-gdrive-token")
        )
        self.credential_manager.store_typed_credential(
            BotTokenCredentials(service_id="slack", bot_token="xoxb-mock-token")
        )
        self.credential_manager.store_typed_credential(
            ApiTokenCredentials(service_id="github", token="ghp_mock-token")
        )

        gmail = GmailConnector(credential_provider=self.credential_manager)
        gcal = GoogleCalendarConnector(credential_provider=self.credential_manager)
        gdrive = GoogleDriveConnector(credential_provider=self.credential_manager)
        slack = SlackConnector(credential_provider=self.credential_manager)
        github = GitHubConnector(credential_provider=self.credential_manager)

        self.service_registry.register(gmail)
        self.service_registry.register(gcal)
        self.service_registry.register(gdrive)
        self.service_registry.register(slack)
        self.service_registry.register(github)

        # Execute read across all 5
        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            session_id=str(self.context.session_id),
        )
        res = await self.service_registry.execute(req, self.context)
        self.assertTrue(res.success)

        req_gh = ServiceRequest(
            service_id="github",
            capability=ServiceCapability.READ,
            operation="list_issues",
            session_id=str(self.context.session_id),
        )
        res_gh = await self.service_registry.execute(req_gh, self.context)
        self.assertTrue(res_gh.success)

        # Health checks
        statuses = await self.service_registry.health_check_all()
        for sid, st in statuses.items():
            self.assertEqual(st, ServiceStatus.CONNECTED)

    # ==========================================
    # 6. Network Safety Configuration & Audit Integrity
    # ==========================================

    def test_external_services_disabled_by_default(self) -> None:
        """10. Verify SystemConfig.enable_external_services defaults to False."""
        config = SystemConfig()
        self.assertFalse(config.enable_external_services)

    def test_audit_trail_and_ipc_secrecy(self) -> None:
        """11. Verify chained audit log and IPC list_services contain zero tokens or secrets."""
        # Store secret
        self.credential_manager.store_typed_credential(
            OAuth2Credentials(service_id="gmail", access_token="ultra-secret-access-token-999")
        )
        gmail = GmailConnector(credential_provider=self.credential_manager)
        self.service_registry.register(gmail)

        # List services for IPC
        services = self.service_registry.list_services()
        svc_json = json.dumps(services)
        self.assertNotIn("ultra-secret", svc_json)
        self.assertNotIn("access_token", svc_json)

        # Audit entries
        entries = self.audit_logger.get_entries()
        for entry in entries:
            entry_str = str(entry)
            self.assertNotIn("ultra-secret", entry_str)


if __name__ == "__main__":
    unittest.main()
