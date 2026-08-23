"""JARVIS External Services Integration Package (Phase 9.1)."""

from services.base import (
    BaseCredentialProvider,
    BaseServiceAdapter,
    InMemoryCredentialProvider,
)
from services.mock_service import MockMessagingServiceAdapter
from services.models import (
    DuplicateServiceError,
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceDisabledError,
    ServiceError,
    ServiceMetadata,
    ServiceNotFoundError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from services.tool_bridge import ServiceTool, register_service_tools

__all__ = [
    "BaseCredentialProvider",
    "BaseServiceAdapter",
    "DuplicateServiceError",
    "InMemoryCredentialProvider",
    "MockMessagingServiceAdapter",
    "ServiceAuthenticationError",
    "ServiceCapability",
    "ServiceDisabledError",
    "ServiceError",
    "ServiceMetadata",
    "ServiceNotFoundError",
    "ServicePermissionBridge",
    "ServiceRegistry",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceStatus",
    "ServiceTool",
    "UndeclaredCapabilityError",
    "register_service_tools",
]
