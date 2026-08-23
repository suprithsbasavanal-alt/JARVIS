"""OS-secure credential storage abstractions (Phase 9.3)."""

from abc import ABC, abstractmethod
import json
import logging
from typing import Any
from services.credentials.models import (
    ApiTokenCredentials,
    BaseCredential,
    BotTokenCredentials,
    CredentialType,
    GenericServiceCredentials,
    OAuth2Credentials,
)

logger = logging.getLogger(__name__)


class SecureStorageError(Exception):
    """Base exception for secure storage operations."""
    pass


class SecureStorageUnavailableError(SecureStorageError):
    """Raised when platform OS secure storage is unavailable and test mode is disabled."""
    pass


class BaseSecureStorage(ABC):
    """Abstract interface for storing and managing encrypted credentials."""

    @abstractmethod
    def store(self, credential: BaseCredential) -> None:
        """Store or update a credential."""
        pass

    @abstractmethod
    def get(self, service_id: str) -> BaseCredential | None:
        """Retrieve a credential by service ID."""
        pass

    @abstractmethod
    def delete(self, service_id: str) -> bool:
        """Delete a credential by service ID."""
        pass

    @abstractmethod
    def has_credential(self, service_id: str) -> bool:
        """Check if a credential exists without loading secret values."""
        pass

    @abstractmethod
    def list_services(self) -> list[str]:
        """List all service IDs currently having stored credentials."""
        pass

    @abstractmethod
    def wipe_all(self) -> None:
        """Purge and zeroize all stored credentials."""
        pass


class InMemorySecureStorage(BaseSecureStorage):
    """In-memory, non-persistent credential storage for unit testing and ephemeral sessions."""

    def __init__(self) -> None:
        self._store: dict[str, BaseCredential] = {}

    def store(self, credential: BaseCredential) -> None:
        self._store[credential.service_id] = credential

    def get(self, service_id: str) -> BaseCredential | None:
        return self._store.get(service_id)

    def delete(self, service_id: str) -> bool:
        if service_id in self._store:
            del self._store[service_id]
            return True
        return False

    def has_credential(self, service_id: str) -> bool:
        return service_id in self._store

    def list_services(self) -> list[str]:
        return list(self._store.keys())

    def wipe_all(self) -> None:
        self._store.clear()

    def __repr__(self) -> str:
        return f"<InMemorySecureStorage(services={list(self._store.keys())})>"


class KeychainSecureStorage(BaseSecureStorage):
    """macOS Keychain secure storage adapter with graceful test fallback."""

    def __init__(self, service_prefix: str = "com.jarvis.assistant.services", allow_in_memory_fallback: bool = True) -> None:
        self.service_prefix = service_prefix
        self.allow_in_memory_fallback = allow_in_memory_fallback
        self._fallback_storage = InMemorySecureStorage()
        self._keyring_available = False

        try:
            import keyring
            self._keyring = keyring
            self._keyring_available = True
        except ImportError:
            self._keyring = None
            if not self.allow_in_memory_fallback:
                raise SecureStorageUnavailableError("Keyring library is not installed and fallback is disallowed.")

    def store(self, credential: BaseCredential) -> None:
        if self._keyring_available and self._keyring is not None:
            try:
                raw_dict = self._serialize_credential(credential)
                self._keyring.set_password(self.service_prefix, credential.service_id, json.dumps(raw_dict))
                return
            except Exception as e:
                logger.warning("Keychain write failed (%s); using in-memory store.", e)

        if self.allow_in_memory_fallback:
            self._fallback_storage.store(credential)
        else:
            raise SecureStorageUnavailableError("Failed to store credential in OS keychain.")

    def get(self, service_id: str) -> BaseCredential | None:
        if self._keyring_available and self._keyring is not None:
            try:
                data_str = self._keyring.get_password(self.service_prefix, service_id)
                if data_str:
                    return self._deserialize_credential(json.loads(data_str))
            except Exception as e:
                logger.warning("Keychain read failed (%s); trying in-memory store.", e)

        return self._fallback_storage.get(service_id)

    def delete(self, service_id: str) -> bool:
        deleted = False
        if self._keyring_available and self._keyring is not None:
            try:
                self._keyring.delete_password(self.service_prefix, service_id)
                deleted = True
            except Exception:
                pass

        fb_deleted = self._fallback_storage.delete(service_id)
        return deleted or fb_deleted

    def has_credential(self, service_id: str) -> bool:
        if self._keyring_available and self._keyring is not None:
            try:
                val = self._keyring.get_password(self.service_prefix, service_id)
                if val is not None:
                    return True
            except Exception:
                pass
        return self._fallback_storage.has_credential(service_id)

    def list_services(self) -> list[str]:
        # For keychain, maintain list via fallback or tracked services
        return self._fallback_storage.list_services()

    def wipe_all(self) -> None:
        for sid in self.list_services():
            self.delete(sid)
        self._fallback_storage.wipe_all()

    def _serialize_credential(self, cred: BaseCredential) -> dict[str, Any]:
        d: dict[str, Any] = {
            "service_id": cred.service_id,
            "credential_type": cred.credential_type.value,
            "created_at": cred.created_at.isoformat(),
            "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
        }
        if isinstance(cred, OAuth2Credentials):
            d.update({
                "access_token": cred.access_token,
                "refresh_token": cred.refresh_token,
                "token_type": cred.token_type,
                "scopes": cred.scopes,
            })
        elif isinstance(cred, ApiTokenCredentials):
            d.update({
                "token": cred.token,
                "username": cred.username,
                "scopes": cred.scopes,
            })
        elif isinstance(cred, BotTokenCredentials):
            d.update({
                "bot_token": cred.bot_token,
                "team_id": cred.team_id,
                "scopes": cred.scopes,
            })
        elif isinstance(cred, GenericServiceCredentials):
            d.update({
                "payload": cred.payload,
            })
        return d

    def _deserialize_credential(self, d: dict[str, Any]) -> BaseCredential:
        ctype = d.get("credential_type")
        sid = d.get("service_id", "")
        if ctype == CredentialType.OAUTH2.value:
            return OAuth2Credentials(
                service_id=sid,
                access_token=d.get("access_token", ""),
                refresh_token=d.get("refresh_token"),
                token_type=d.get("token_type", "Bearer"),
                scopes=d.get("scopes", []),
            )
        elif ctype == CredentialType.API_TOKEN.value:
            return ApiTokenCredentials(
                service_id=sid,
                token=d.get("token", ""),
                username=d.get("username"),
                scopes=d.get("scopes", []),
            )
        elif ctype == CredentialType.BOT_TOKEN.value:
            return BotTokenCredentials(
                service_id=sid,
                bot_token=d.get("bot_token", ""),
                team_id=d.get("team_id"),
                scopes=d.get("scopes", []),
            )
        return GenericServiceCredentials(
            service_id=sid,
            payload=d.get("payload", {}),
        )
