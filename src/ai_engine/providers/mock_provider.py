"""Mock & Local Fallback LLM Provider Implementation."""

from typing import AsyncGenerator
from src.ai_engine.contracts.provider import BaseLLMProvider, LLMRequest, LLMResponse
from src.shared.logger.logger import get_logger

logger = get_logger("ai_engine.mock_provider")


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for testing and offline fallback."""

    def __init__(self, response_override: str = None) -> None:
        self._response_override = response_override

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        logger.info(f"Generating mock completion for prompt: '{request.prompt[:50]}...'")
        output_text = self._response_override or f"Jarvis Mock Response to: '{request.prompt}'"
        return LLMResponse(
            content=output_text,
            raw_response={"provider": "mock", "prompt": request.prompt},
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(output_text.split()),
            tool_calls=None
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        output_text = self._response_override or f"Jarvis Mock Response to: '{request.prompt}'"
        words = output_text.split()
        for word in words:
            yield word + " "
