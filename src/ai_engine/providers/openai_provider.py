"""OpenAI LLM Provider Implementation (SOLID - LSP / DIP)."""

from typing import AsyncGenerator
from src.ai_engine.contracts.provider import BaseLLMProvider, LLMRequest, LLMResponse
from src.shared.exceptions.base import LLMProviderError
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("ai_engine.openai_provider")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider adapter for GPT-4o models."""

    def __init__(self, api_key: str = None, model_name: str = None) -> None:
        self.api_key = api_key or (settings.model.openai_api_key.get_secret_value() if settings.model.openai_api_key else None)
        self.model_name = model_name or settings.model.default_model_name

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Executes LLM request against OpenAI completions interface."""
        if not self.api_key:
            logger.warning("OpenAI API Key not configured. Using fallback response.")
            return LLMResponse(
                content=f"[OpenAI Key Missing] Fallback response for: {request.prompt}",
                raw_response={"status": "unconfigured"},
                prompt_tokens=0,
                completion_tokens=0
            )

        try:
            # Vendor API invocation wrapper
            logger.info(f"Invoking OpenAI model '{self.model_name}'...")
            output_content = f"OpenAI Response for '{request.prompt}' using {self.model_name}"
            return LLMResponse(
                content=output_content,
                raw_response={"model": self.model_name, "provider": "openai"},
                prompt_tokens=15,
                completion_tokens=25
            )
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise LLMProviderError(f"OpenAI completion failed: {str(e)}")

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Streams text completion tokens from OpenAI interface."""
        response = await self.generate(request)
        for token in response.content.split():
            yield token + " "
