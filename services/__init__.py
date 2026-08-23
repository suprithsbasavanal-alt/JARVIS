"""JARVIS External Services Integration Package (Phase 9)."""

from services.base import (
    BaseCredentialProvider,
    BaseServiceAdapter,
    InMemoryCredentialProvider,
)
from services.connectors import (
    BaseHermeticConnector,
    ConnectorSimulationConfig,
    GitHubConnector,
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    ServiceOutageError,
    ServiceRateLimitError,
    ServiceTimeoutError,
    SlackConnector,
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
    "BaseHermeticConnector",
    "BaseServiceAdapter",
    "ConnectorSimulationConfig",
    "DuplicateServiceError",
    "GitHubConnector",
    "GmailConnector",
    "GoogleCalendarConnector",
    "GoogleDriveConnector",
    "InMemoryCredentialProvider",
    "MockMessagingServiceAdapter",
    "ServiceAuthenticationError",
    "ServiceCapability",
    "ServiceDisabledError",
    "ServiceError",
    "ServiceMetadata",
    "ServiceNotFoundError",
    "ServiceOutageError",
    "ServicePermissionBridge",
    "ServiceRateLimitError",
    "ServiceRegistry",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceStatus",
    "ServiceTimeoutError",
    "ServiceTool",
    "SlackConnector",
    "UndeclaredCapabilityError",
    "register_service_tools",
]
