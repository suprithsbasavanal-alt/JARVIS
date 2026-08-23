"""Secure Credential Manager implementing BaseCredentialProvider (Phase 9.3)."""

from typing import Any
from services.base import BaseCredentialProvider
from services.credentials.models import (
    ApiTokenCredentials,
    BaseCredential,
    BotTokenCredentials,
    GenericServiceCredentials,
    OAuth2Credentials,
)
from services.credentials.storage import BaseSecureStorage, InMemorySecureStorage


class SecureCredentialManager(BaseCredentialProvider):
    """Production-grade credential manager with OS secure storage and typed credential models."""

    def __init__(self, storage: BaseSecureStorage | None = None) -> None:
        self.storage: BaseSecureStorage = storage or InMemorySecureStorage()

    def has_credentials(self, service_id: str) -> bool:
        """Check if credentials exist for a service."""
        return self.storage.has_credential(service_id)

    def get_credential(self, service_id: str, key: str) -> str | None:
        """Retrieve a specific credential value (e.g. 'oauth_token', 'access_token', 'bot_token')."""
        cred = self.storage.get(service_id)
        if not cred:
            return None

        if isinstance(cred, OAuth2Credentials):
            if key in {"access_token", "oauth_token", "token"}:
                return cred.access_token
            if key == "refresh_token":
                return cred.refresh_token
        elif isinstance(cred, ApiTokenCredentials):
            if key in {"token", "pat_token", "api_token"}:
                return cred.token
        elif isinstance(cred, BotTokenCredentials):
            if key in {"bot_token", "token"}:
                return cred.bot_token
        elif isinstance(cred, GenericServiceCredentials):
            return cred.payload.get(key)

        return None

    def set_credential(self, service_id: str, key: str, value: str) -> None:
        """Store or update a credential value as a GenericServiceCredential or typed model."""
        existing = self.storage.get(service_id)
        if isinstance(existing, GenericServiceCredentials):
            existing.payload[key] = value
            self.storage.store(existing)
        elif isinstance(existing, OAuth2Credentials):
            if key in {"access_token", "oauth_token", "token"}:
                existing.access_token = value
            elif key == "refresh_token":
                existing.refresh_token = value
            self.storage.store(existing)
        elif isinstance(existing, ApiTokenCredentials):
            if key in {"token", "pat_token", "api_token"}:
                existing.token = value
            self.storage.store(existing)
        elif isinstance(existing, BotTokenCredentials):
            if key in {"bot_token", "token"}:
                existing.bot_token = value
            self.storage.store(existing)
        else:
            # Create a GenericServiceCredentials or match by key naming convention
            if key in {"oauth_token", "access_token"}:
                self.storage.store(OAuth2Credentials(service_id=service_id, access_token=value))
            elif key == "bot_token":
                self.storage.store(BotTokenCredentials(service_id=service_id, bot_token=value))
            elif key in {"pat_token", "api_token"}:
                self.storage.store(ApiTokenCredentials(service_id=service_id, token=value))
            else:
                self.storage.store(GenericServiceCredentials(service_id=service_id, payload={key: value}))

    def store_typed_credential(self, credential: BaseCredential) -> None:
        """Store a typed credential object directly."""
        self.storage.store(credential)

    def get_typed_credential(self, service_id: str) -> BaseCredential | None:
        """Retrieve the typed credential object."""
        return self.storage.get(service_id)

    def rotate_credential(self, service_id: str, key: str, new_value: str) -> None:
        """Rotate a specific credential value."""
        self.set_credential(service_id, key, new_value)

    def rotate_typed_credential(self, new_credential: BaseCredential) -> None:
        """Atomically replace an existing typed credential."""
        self.storage.store(new_credential)

    def revoke_credentials(self, service_id: str) -> None:
        """Zeroize and remove credentials for a service."""
        self.storage.delete(service_id)

    def wipe_all(self) -> None:
        """Zeroize all stored credentials across all services."""
        self.storage.wipe_all()

    def get_credential_metadata(self, service_id: str) -> dict[str, Any] | None:
        """Return safe, non-sensitive credential status and expiration metadata."""
        cred = self.storage.get(service_id)
        if not cred:
            return None
        return cred.to_safe_dict()

    def __repr__(self) -> str:
        services = self.storage.list_services()
        return f"<SecureCredentialManager(stored_services={services}, secrets=[REDACTED])>"

    def __str__(self) -> str:
        return self.__repr__()
