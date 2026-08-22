"""Abstract Model Provider Interface."""

from abc import ABC, abstractmethod
from model_routing.schemas import ModelRequest, ModelResponse


class BaseModelProvider(ABC):
    """Abstract interface for all model execution backends."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Execute model inference on the given request."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check availability of the model provider."""
        pass
