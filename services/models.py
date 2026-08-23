"""Data models and capability contracts for external service integrations (Phase 9.1)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class ServiceCapability(str, Enum):
    """Granular capability permissions that external service adapters can declare."""
    READ = "READ"          # Read-only resource retrieval (e.g. read inbox, get event)
    SEARCH = "SEARCH"      # Query and search indexing (e.g. search messages, find contacts)
    CREATE = "CREATE"      # Resource creation (e.g. create draft, create note)
    UPDATE = "UPDATE"      # Resource modification (e.g. edit calendar event, update contact)
    DELETE = "DELETE"      # Resource removal (e.g. delete note, cancel event)
    SEND = "SEND"          # Outbound transmission (e.g. send email, send chat message)
    EXECUTE = "EXECUTE"    # Service-side action execution (e.g. trigger webhook, run automation)


class ServiceStatus(str, Enum):
    """Lifecycle and health status states of a registered service adapter."""
    CONNECTED = "CONNECTED"          # Active, healthy, credentials valid
    DISCONNECTED = "DISCONNECTED"    # Configured but currently offline
    AUTH_REQUIRED = "AUTH_REQUIRED"  # Credentials missing, expired, or require re-auth
    DEGRADED = "DEGRADED"            # Experiencing elevated latency or transient rate-limits
    REVOKED = "REVOKED"              # Explicitly revoked/disabled by user
    ERROR = "ERROR"                  # Unrecoverable error state


@dataclass(frozen=True)
class ServiceMetadata:
    """Immutable public metadata describing a registered service adapter."""
    service_id: str
    name: str
    description: str
    capabilities: frozenset[ServiceCapability]
    version: str = "1.0.0"
    auth_type: str = "OAUTH2"
    is_enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return safe, non-sensitive metadata dictionary for IPC/UI inspection."""
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "version": self.version,
            "auth_type": self.auth_type,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at,
        }


@dataclass
class ServiceRequest:
    """Typed request payload dispatched to an external service adapter."""
    service_id: str
    capability: ServiceCapability
    operation: str
    parameters: dict[str, Any] = field(default_factory=dict)
    session_id: str = "system"
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ServiceResponse:
    """Standardized response from an external service adapter."""
    service_id: str
    operation: str
    success: bool
    data: Any = None
    error: str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "operation": self.operation,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


class ServiceError(Exception):
    """Base exception for service integration errors."""
    pass


class ServiceNotFoundError(ServiceError):
    """Raised when querying an unregistered service ID."""
    pass


class DuplicateServiceError(ServiceError):
    """Raised when registering an already existing service ID."""
    pass


class ServiceDisabledError(ServiceError):
    """Raised when invoking an operation on a disabled or revoked service."""
    pass


class UndeclaredCapabilityError(ServiceError):
    """Raised when an operation requests a capability not declared by the adapter."""
    pass


class ServiceAuthenticationError(ServiceError):
    """Raised when service credentials are missing or invalid."""
    pass
