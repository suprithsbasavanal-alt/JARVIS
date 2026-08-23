"""Common infrastructure, simulation hooks, and base connector classes for Phase 9.2."""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from services.base import BaseCredentialProvider, BaseServiceAdapter, InMemoryCredentialProvider
from services.models import (
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceError,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)


class ServiceRateLimitError(ServiceError):
    """Raised when an external service is rate-limited / throttled."""
    pass


class ServiceOutageError(ServiceError):
    """Raised when an external service is experiencing an upstream outage (HTTP 5xx)."""
    pass


class ServiceTimeoutError(ServiceError):
    """Raised when an external service call times out."""
    pass


@dataclass
class ConnectorSimulationConfig:
    """Configurable simulation hooks for testing failure modes hermetically."""
    simulate_auth_failure: bool = False
    simulate_rate_limit: bool = False
    simulate_timeout: bool = False
    simulate_outage: bool = False
    simulated_latency_seconds: float = 0.0


from services.transport.base import BaseHttpTransport


class BaseHermeticConnector(BaseServiceAdapter):
    """Base class for Phase 9.2 & 9.4 hermetic service connectors with simulation hooks and transport injection."""

    def __init__(
        self,
        metadata: ServiceMetadata,
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
        transport: BaseHttpTransport | None = None,
    ) -> None:
        super().__init__(metadata=metadata, credential_provider=credential_provider)
        self.simulation_config = simulation_config or ConnectorSimulationConfig()
        self.transport = transport
        self._status: ServiceStatus = ServiceStatus.CONNECTED

    async def _apply_simulations(self) -> None:
        """Apply configured simulation modes before executing requests."""
        if self.simulation_config.simulate_timeout:
            # Sleep longer than the 15s execution timeout or raise timeout
            await asyncio.sleep(0.01)
            raise ServiceTimeoutError(f"Simulated timeout communicating with '{self.service_id}'.")

        if self.simulation_config.simulated_latency_seconds > 0:
            await asyncio.sleep(self.simulation_config.simulated_latency_seconds)

        if self.simulation_config.simulate_rate_limit:
            self._status = ServiceStatus.DEGRADED
            raise ServiceRateLimitError(f"Rate limit exceeded (HTTP 429) for service '{self.service_id}'.")

        if self.simulation_config.simulate_outage:
            self._status = ServiceStatus.ERROR
            raise ServiceOutageError(f"Upstream service outage (HTTP 503) on '{self.service_id}'.")

        if self.simulation_config.simulate_auth_failure or not self.credential_provider.has_credentials(self.service_id):
            self._status = ServiceStatus.AUTH_REQUIRED
            raise ServiceAuthenticationError(f"Missing or invalid credentials for service '{self.service_id}'.")

    async def health_check(self) -> ServiceStatus:
        """Evaluate connector health and authentication status."""
        if not self.is_enabled:
            self._status = ServiceStatus.DISCONNECTED
            return self._status

        if self.simulation_config.simulate_outage:
            self._status = ServiceStatus.ERROR
            return self._status

        if self.simulation_config.simulate_rate_limit:
            self._status = ServiceStatus.DEGRADED
            return self._status

        if self.simulation_config.simulate_auth_failure or not self.credential_provider.has_credentials(self.service_id):
            self._status = ServiceStatus.AUTH_REQUIRED
            return self._status

        self._status = ServiceStatus.CONNECTED
        return self._status

    async def disconnect(self) -> None:
        """Disconnect connector."""
        self._status = ServiceStatus.DISCONNECTED

    async def revoke(self) -> None:
        """Zeroize credentials and revoke connector."""
        self.credential_provider.revoke_credentials(self.service_id)
        self._status = ServiceStatus.REVOKED
        self.is_enabled = False
