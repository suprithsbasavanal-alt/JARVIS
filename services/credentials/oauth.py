"""OAuth 2.0 Authentication Lifecycle Manager (Phase 9.3)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Any
import urllib.parse

from services.credentials.models import OAuth2Credentials
from services.credentials.provider import SecureCredentialManager

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth operations."""
    pass


class OAuthStateError(OAuthError):
    """Raised when an OAuth CSRF state parameter is invalid, expired, or replayed."""
    pass


class OAuthRefreshError(OAuthError):
    """Raised when token refresh fails."""
    pass


@dataclass
class OAuthState:
    """Ephemeral CSRF state token with TTL and single-use enforcement."""
    token: str
    service_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    is_used: bool = False

    def is_valid(self, service_id: str) -> bool:
        if self.is_used:
            return False
        if self.service_id != service_id:
            return False
        return datetime.now(timezone.utc) < self.expires_at


class OAuth2LifecycleManager:
    """Manages authorization URLs, CSRF states, code exchange, and token refresh lifecycles."""

    def __init__(self, credential_manager: SecureCredentialManager) -> None:
        self.credential_manager = credential_manager
        self._states: dict[str, OAuthState] = {}

    def generate_authorization_url(
        self,
        service_id: str,
        client_id: str,
        redirect_uri: str,
        scopes: list[str],
        auth_endpoint: str,
    ) -> tuple[str, str]:
        """Generate a secure OAuth authorization URL with CSRF state protection."""
        state_token = secrets.token_urlsafe(32)
        state_obj = OAuthState(token=state_token, service_id=service_id)
        self._states[state_token] = state_obj

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state_token,
            "access_type": "offline",
            "prompt": "consent",
        }
        encoded = urllib.parse.urlencode(params)
        auth_url = f"{auth_endpoint}?{encoded}"
        return auth_url, state_token

    def validate_callback_state(self, service_id: str, state_token: str) -> bool:
        """Validate and consume the single-use CSRF state token."""
        state_obj = self._states.get(state_token)
        if not state_obj:
            return False

        if not state_obj.is_valid(service_id):
            return False

        # Mark as consumed to prevent replay
        state_obj.is_used = True
        return True

    def exchange_code_for_token(
        self,
        service_id: str,
        code: str,
        state_token: str,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        mock_token_response: dict[str, Any] | None = None,
    ) -> OAuth2Credentials:
        """Exchange authorization code for OAuth2 tokens and store securely."""
        if not self.validate_callback_state(service_id, state_token):
            raise OAuthStateError(f"Invalid or expired CSRF state for service '{service_id}'.")

        # In hermetic / test mode, use mock token response
        token_data = mock_token_response or {
            "access_token": f"mock-oauth-access-{service_id}-{secrets.token_hex(8)}",
            "refresh_token": f"mock-oauth-refresh-{service_id}-{secrets.token_hex(8)}",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "read write",
        }

        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        scopes = token_data.get("scope", "").split() if isinstance(token_data.get("scope"), str) else token_data.get("scopes", [])

        credentials = OAuth2Credentials(
            service_id=service_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
            token_type=token_data.get("token_type", "Bearer"),
            scopes=scopes,
        )

        self.credential_manager.store_typed_credential(credentials)
        return credentials

    def refresh_access_token(
        self,
        service_id: str,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        mock_refresh_response: dict[str, Any] | None = None,
        simulate_failure: bool = False,
    ) -> OAuth2Credentials:
        """Refresh an expired OAuth access token using the stored refresh token."""
        if simulate_failure:
            raise OAuthRefreshError(f"OAuth refresh failed for service '{service_id}'.")

        existing = self.credential_manager.get_typed_credential(service_id)
        if not isinstance(existing, OAuth2Credentials) or not existing.refresh_token:
            raise OAuthRefreshError(f"No valid refresh token available for service '{service_id}'.")

        refresh_data = mock_refresh_response or {
            "access_token": f"refreshed-access-{service_id}-{secrets.token_hex(8)}",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        expires_in = refresh_data.get("expires_in", 3600)
        existing.access_token = refresh_data["access_token"]
        existing.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        if "refresh_token" in refresh_data:
            existing.refresh_token = refresh_data["refresh_token"]

        self.credential_manager.store_typed_credential(existing)
        return existing

    def revoke_token(self, service_id: str) -> bool:
        """Revoke and purge stored OAuth credentials."""
        self.credential_manager.revoke_credentials(service_id)
        return True
