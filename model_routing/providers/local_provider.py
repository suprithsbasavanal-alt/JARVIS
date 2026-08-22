"""Local Offline Model Provider Interface (Ollama / Llama.cpp / vLLM)."""

from model_routing.base import BaseModelProvider
from model_routing.schemas import ModelRequest, ModelResponse


class LocalModelProvider(BaseModelProvider):
    """Abstract connector for local on-device inference engines."""

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", provider_name: str = "local-ollama") -> None:
        super().__init__(provider_name)
        self.endpoint = endpoint

    async def generate(self, request: ModelRequest) -> ModelResponse:
        # In Phase 0: Stubbed out to ensure safe hermetic execution
        return ModelResponse(
            model_name="local-stub",
            provider_name=self.provider_name,
            content="[LOCAL MODEL INFERENCE STUB: Phase 0 Safe Development Mode]",
        )

    async def is_healthy(self) -> bool:
        return True
