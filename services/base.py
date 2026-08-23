"""Base abstractions for External Service Adapters and Credential Providers (Phase 9.1)."""

from abc import ABC, abstractmethod
from typing import Any
from services.models import (
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)


class BaseCredentialProvider(ABC):
    """Abstract credential provider ensuring platform secrets are isolated and never exposed in plaintext."""

    @abstractmethod
    def has_credentials(self, service_id: str) -> bool:
        """Check if active credentials exist for the given service."""
        pass

    @abstractmethod
    def get_credential(self, service_id: str, key: str) -> str | None:
        """Retrieve a specific credential value for internal adapter authentication."""
        pass

    @abstractmethod
    def set_credential(self, service_id: str, key: str, value: str) -> None:
        """Store a sensitive credential."""
        pass

    @abstractmethod
    def rotate_credential(self, service_id: str, key: str, new_value: str) -> None:
        """Atomically update/rotate an existing credential."""
        pass

    @abstractmethod
    def revoke_credentials(self, service_id: str) -> None:
        """Zeroize and remove all credentials associated with a service ID."""
        pass

    @abstractmethod
    def wipe_all(self) -> None:
        """Zeroize all stored credentials across all services."""
        pass


class InMemoryCredentialProvider(BaseCredentialProvider):
    """Hermetic in-memory credential provider for testing and isolated dev environments."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    def has_credentials(self, service_id: str) -> bool:
        return service_id in self._store and bool(self._store[service_id])

    def get_credential(self, service_id: str, key: str) -> str | None:
        return self._store.get(service_id, {}).get(key)

    def set_credential(self, service_id: str, key: str, value: str) -> None:
        if service_id not in self._store:
            self._store[service_id] = {}
        self._store[service_id][key] = value

    def rotate_credential(self, service_id: str, key: str, new_value: str) -> None:
        if service_id not in self._store:
            self._store[service_id] = {}
        self._store[service_id][key] = new_value

    def revoke_credentials(self, service_id: str) -> None:
        self._store.pop(service_id, None)

    def wipe_all(self) -> None:
        self._store.clear()

    def __repr__(self) -> str:
        return f"<InMemoryCredentialProvider (services_count={len(self._store)}, credentials=[REDACTED])>"

    def __str__(self) -> str:
        return self.__repr__()


class BaseServiceAdapter(ABC):
    """Abstract base class for all external service adapters (Gmail, Calendar, WhatsApp, etc.)."""

    def __init__(
        self,
        metadata: ServiceMetadata,
        credential_provider: BaseCredentialProvider | None = None,
    ) -> None:
        self.metadata = metadata
        self.credential_provider = credential_provider or InMemoryCredentialProvider()
        self._status: ServiceStatus = ServiceStatus.DISCONNECTED
        self._is_enabled: bool = metadata.is_enabled

    @property
    def service_id(self) -> str:
        return self.metadata.service_id

    @property
    def capabilities(self) -> frozenset[ServiceCapability]:
        return self.metadata.capabilities

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, value: bool) -> None:
        self._is_enabled = value
        if not value and self._status != ServiceStatus.REVOKED:
            self._status = ServiceStatus.DISCONNECTED

    @property
    def status(self) -> ServiceStatus:
        return self._status

    def validate_capability(self, capability: ServiceCapability) -> None:
        """Verify that the requested capability is explicitly declared by this adapter."""
        if capability not in self.capabilities:
            raise UndeclaredCapabilityError(
                f"Service '{self.service_id}' does not declare capability '{capability.value}'."
            )

    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Perform a non-blocking diagnostic check on the service connectivity and credentials."""
        pass

    @abstractmethod
    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute a service operation within capability and permission boundaries."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect active sessions without revoking persistent registration."""
        pass

    @abstractmethod
    async def revoke(self) -> None:
        """Revoke all active tokens, zeroize credentials, and disable adapter."""
        pass
