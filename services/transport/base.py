"""Abstract base class for external HTTP transport (Phase 9.4)."""

from abc import ABC, abstractmethod
from services.transport.models import HttpRequest, HttpResponse


class BaseHttpTransport(ABC):
    """Abstract HTTP client interface for external service communication."""

    @abstractmethod
    async def send(self, request: HttpRequest) -> HttpResponse:
        """Asynchronously send an HTTP request and return the response."""
        pass
