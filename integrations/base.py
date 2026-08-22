"""Base Integration Contract and Lifecycle."""

from abc import ABC, abstractmethod


class BaseIntegration(ABC):
    """Abstract base for all third-party external service connectors."""

    def __init__(self, service_name: str, is_mock: bool = True) -> None:
        self.service_name = service_name
        self.is_mock = is_mock

    @abstractmethod
    async def is_available(self) -> bool:
        """Check availability and authorization status."""
        pass
