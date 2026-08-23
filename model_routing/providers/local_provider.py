"""Local Offline Model Provider Interface (Ollama / Local Inference)."""

from model_routing.base import BaseModelProvider
from model_routing.providers.ollama_provider import OllamaModelProvider
from model_routing.schemas import ModelRequest, ModelResponse


class LocalModelProvider(OllamaModelProvider):
    """Local on-device inference provider backed by Ollama engine."""

    def __init__(
        self,
        endpoint: str | None = None,
        model_name: str | None = None,
        provider_name: str = "local-ollama",
    ) -> None:
        super().__init__(
            base_url=endpoint,
            model_name=model_name,
            provider_name=provider_name,
        )

