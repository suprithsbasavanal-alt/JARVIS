"""Secure Credentials and Authentication Package for JARVIS Phase 9.3."""

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
    OAuthError,
    OAuthRefreshError,
    OAuthState,
    OAuthStateError,
)
from services.credentials.provider import SecureCredentialManager
from services.credentials.storage import (
    BaseSecureStorage,
    InMemorySecureStorage,
    KeychainSecureStorage,
    SecureStorageError,
    SecureStorageUnavailableError,
)

__all__ = [
    "ApiTokenCredentials",
    "BaseCredential",
    "BaseSecureStorage",
    "BotTokenCredentials",
    "CredentialType",
    "GenericServiceCredentials",
    "GitHubAuthAdapter",
    "GmailAuthAdapter",
    "GoogleCalendarAuthAdapter",
    "GoogleDriveAuthAdapter",
    "InMemorySecureStorage",
    "KeychainSecureStorage",
    "OAuth2Credentials",
    "OAuth2LifecycleManager",
    "OAuthError",
    "OAuthRefreshError",
    "OAuthState",
    "OAuthStateError",
    "SecureCredentialManager",
    "SecureStorageError",
    "SecureStorageUnavailableError",
    "SlackAuthAdapter",
]
