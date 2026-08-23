"""Service-specific authentication adapters and scope configurations (Phase 9.3)."""

from typing import Any
from services.credentials.models import (
    ApiTokenCredentials,
    BotTokenCredentials,
    OAuth2Credentials,
)
from services.credentials.oauth import OAuth2LifecycleManager
from services.credentials.provider import SecureCredentialManager
from services.models import ServiceAuthenticationError


class GmailAuthAdapter:
    """OAuth2 authentication handler for Gmail."""
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(self, oauth_manager: OAuth2LifecycleManager) -> None:
        self.oauth_manager = oauth_manager

    def get_auth_url(self, client_id: str, redirect_uri: str, custom_scopes: list[str] | None = None) -> tuple[str, str]:
        scopes = custom_scopes or self.DEFAULT_SCOPES
        return self.oauth_manager.generate_authorization_url(
            service_id="gmail",
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            auth_endpoint=self.AUTH_ENDPOINT,
        )

    def authenticate_code(self, code: str, state: str, client_id: str, client_secret: str, mock_data: dict[str, Any] | None = None) -> OAuth2Credentials:
        return self.oauth_manager.exchange_code_for_token(
            service_id="gmail",
            code=code,
            state_token=state,
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=self.TOKEN_ENDPOINT,
            mock_token_response=mock_data,
        )


class GoogleCalendarAuthAdapter:
    """OAuth2 authentication handler for Google Calendar."""
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    def __init__(self, oauth_manager: OAuth2LifecycleManager) -> None:
        self.oauth_manager = oauth_manager

    def get_auth_url(self, client_id: str, redirect_uri: str, custom_scopes: list[str] | None = None) -> tuple[str, str]:
        scopes = custom_scopes or self.DEFAULT_SCOPES
        return self.oauth_manager.generate_authorization_url(
            service_id="google_calendar",
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            auth_endpoint=self.AUTH_ENDPOINT,
        )

    def authenticate_code(self, code: str, state: str, client_id: str, client_secret: str, mock_data: dict[str, Any] | None = None) -> OAuth2Credentials:
        return self.oauth_manager.exchange_code_for_token(
            service_id="google_calendar",
            code=code,
            state_token=state,
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=self.TOKEN_ENDPOINT,
            mock_token_response=mock_data,
        )


class GoogleDriveAuthAdapter:
    """OAuth2 authentication handler for Google Drive."""
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self, oauth_manager: OAuth2LifecycleManager) -> None:
        self.oauth_manager = oauth_manager

    def get_auth_url(self, client_id: str, redirect_uri: str, custom_scopes: list[str] | None = None) -> tuple[str, str]:
        scopes = custom_scopes or self.DEFAULT_SCOPES
        return self.oauth_manager.generate_authorization_url(
            service_id="google_drive",
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            auth_endpoint=self.AUTH_ENDPOINT,
        )

    def authenticate_code(self, code: str, state: str, client_id: str, client_secret: str, mock_data: dict[str, Any] | None = None) -> OAuth2Credentials:
        return self.oauth_manager.exchange_code_for_token(
            service_id="google_drive",
            code=code,
            state_token=state,
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=self.TOKEN_ENDPOINT,
            mock_token_response=mock_data,
        )


class SlackAuthAdapter:
    """Bot token authentication handler for Slack."""
    DEFAULT_SCOPES = ["channels:history", "chat:write", "search:read"]

    def __init__(self, credential_manager: SecureCredentialManager) -> None:
        self.credential_manager = credential_manager

    def authenticate_bot_token(self, bot_token: str, team_id: str | None = None, scopes: list[str] | None = None) -> BotTokenCredentials:
        if not bot_token or not bot_token.strip():
            raise ServiceAuthenticationError("Invalid or empty Slack bot token.")
        
        credentials = BotTokenCredentials(
            service_id="slack",
            bot_token=bot_token.strip(),
            team_id=team_id,
            scopes=scopes or self.DEFAULT_SCOPES,
        )
        self.credential_manager.store_typed_credential(credentials)
        return credentials


class GitHubAuthAdapter:
    """Personal Access Token (PAT) authentication handler for GitHub."""
    DEFAULT_SCOPES = ["repo", "read:org", "issues"]

    def __init__(self, credential_manager: SecureCredentialManager) -> None:
        self.credential_manager = credential_manager

    def authenticate_pat(self, token: str, username: str | None = None, scopes: list[str] | None = None) -> ApiTokenCredentials:
        if not token or not token.strip():
            raise ServiceAuthenticationError("Invalid or empty GitHub personal access token.")

        credentials = ApiTokenCredentials(
            service_id="github",
            token=token.strip(),
            username=username,
            scopes=scopes or self.DEFAULT_SCOPES,
        )
        self.credential_manager.store_typed_credential(credentials)
        return credentials
