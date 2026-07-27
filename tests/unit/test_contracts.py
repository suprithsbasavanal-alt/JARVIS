"""Unit Test Suite for Jarvis Domain Contracts & Dependency Injection."""

import pytest
from src.backend.container.di_container import Container
from src.ai_engine.contracts.provider import BaseLLMProvider, LLMRequest, LLMResponse
from src.shared.exceptions.base import JarvisException


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM Provider for unit testing DIP compliance."""

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=f"Echo: {request.prompt}",
            raw_response={"mock": True}
        )

    async def generate_stream(self, request: LLMRequest):
        yield "Echo: "
        yield request.prompt


def test_container_registration_and_resolution():
    """Verifies dependency injection container binds contracts to implementations."""
    container = Container()
    mock_instance = MockLLMProvider()
    container.register_singleton(BaseLLMProvider, mock_instance)

    resolved = container.resolve(BaseLLMProvider)
    assert resolved.provider_name == "mock_provider"


@pytest.mark.asyncio
async def test_mock_llm_execution():
    """Verifies mock provider returns compliant LLMResponse."""
    provider = MockLLMProvider()
    req = LLMRequest(prompt="Hello Jarvis")
    res = await provider.generate(req)
    assert res.content == "Echo: Hello Jarvis"


def test_jarvis_exception():
    """Verifies domain exception structure."""
    exc = JarvisException("Test Error", code="TEST_CODE")
    assert exc.code == "TEST_CODE"
    assert str(exc) == "Test Error"
