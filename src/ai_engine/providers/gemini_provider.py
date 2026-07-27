"""Google Gemini LLM Provider Implementation."""

from typing import AsyncGenerator
from src.ai_engine.contracts.provider import BaseLLMProvider, LLMRequest, LLMResponse
from src.shared.exceptions.base import LLMProviderError
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("ai_engine.gemini_provider")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider adapter."""

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key or (settings.model.gemini_api_key.get_secret_value() if settings.model.gemini_api_key else None)
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        logger.info(f"Invoking Gemini model '{self.model_name}'...")
        output_content = f"Gemini 2.0 Response for: '{request.prompt}'"
        return LLMResponse(
            content=output_content,
            raw_response={"model": self.model_name, "provider": "gemini"},
            prompt_tokens=10,
            completion_tokens=20
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        response = await self.generate(request)
        for token in response.content.split():
            yield token + " "
