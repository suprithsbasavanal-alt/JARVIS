"""Cloud Model Provider Interface (Gemini / Claude / OpenAI)."""

from model_routing.base import BaseModelProvider
from model_routing.schemas import ModelRequest, ModelResponse


class CloudModelProvider(BaseModelProvider):
    """Abstract connector for external cloud model APIs."""

    def __init__(self, provider_name: str = "cloud-provider", api_key: str | None = None) -> None:
        super().__init__(provider_name)
        self.api_key = api_key

    async def generate(self, request: ModelRequest) -> ModelResponse:
        # In Phase 0: Stubbed out to prevent external network calls
        return ModelResponse(
            model_name="cloud-stub",
            provider_name=self.provider_name,
            content="[CLOUD MODEL INFERENCE STUB: Phase 0 Safe Development Mode]",
        )

    async def is_healthy(self) -> bool:
        return True
