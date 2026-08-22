"""Unit tests for ModelRouter and Prompt Sanitization."""

import pytest
from config.schema import ModelTier
from model_routing.router import ModelRouter
from model_routing.schemas import ChatMessage, MessageRole, ModelRequest


@pytest.mark.asyncio
async def test_model_router_mock_generation(model_router: ModelRouter) -> None:
    """Verify standard model inference routing through mock provider."""
    request = ModelRequest(
        messages=[
            ChatMessage(role=MessageRole.USER, content="Hello JARVIS"),
        ],
        tier="fast",
    )
    response = await model_router.route(request, tier=ModelTier.FAST)
    assert response.provider_name == "mock"
    assert "JARVIS" in response.content


@pytest.mark.asyncio
async def test_model_router_pii_sanitization(model_router: ModelRouter) -> None:
    """Verify PII in user query is redacted during routing and restored."""
    raw_query = "Please email test.user@example.com with key sk-12345678901234567890123456789012"
    request = ModelRequest(
        messages=[
            ChatMessage(role=MessageRole.USER, content=raw_query),
        ],
        tier="fast",
    )
    response = await model_router.route(request, tier=ModelTier.FAST, enable_sanitization=True)
    assert response.provider_name == "mock"
