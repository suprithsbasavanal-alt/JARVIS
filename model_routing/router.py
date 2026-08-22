"""Multi-Tier Dynamic Model Router with Sanitization and Fallback."""

from config.schema import ModelsConfig, ModelTier
from core.exceptions import ModelRoutingError
from model_routing.base import BaseModelProvider
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.schemas import ChatMessage, ModelRequest, ModelResponse
from security.sanitizer import Sanitizer


class ModelRouter:
    """Orchestrates model requests across Fast, Reasoning, and Local Private tiers."""

    def __init__(
        self,
        config: ModelsConfig | None = None,
        sanitizer: Sanitizer | None = None,
    ) -> None:
        self.config = config or ModelsConfig()
        self.sanitizer = sanitizer or Sanitizer()
        self._providers: dict[str, BaseModelProvider] = {}
        # Register default fallback mock provider
        self.register_provider("mock", MockModelProvider("mock"))

    def register_provider(self, name: str, provider: BaseModelProvider) -> None:
        """Register a model execution provider."""
        self._providers[name] = provider

    def get_provider_for_tier(self, tier: ModelTier) -> BaseModelProvider:
        """Resolve the appropriate provider backend for the requested tier."""
        tier_config_map = {
            ModelTier.FAST: self.config.fast_tier,
            ModelTier.REASONING: self.config.reasoning_tier,
            ModelTier.LOCAL_PRIVATE: self.config.local_private_tier,
        }
        tier_cfg = tier_config_map.get(tier, self.config.fast_tier)
        provider = self._providers.get(tier_cfg.provider)

        if not provider:
            # Fall back to mock provider in development
            provider = self._providers.get("mock")
            if not provider:
                raise ModelRoutingError(f"No provider available for tier '{tier.value}'")

        return provider

    async def route(
        self,
        request: ModelRequest,
        tier: ModelTier = ModelTier.FAST,
        enable_sanitization: bool = True,
    ) -> ModelResponse:
        """Route request through sanitization, tier dispatching, and response restoration."""
        provider = self.get_provider_for_tier(tier)

        # Sanitize prompt if enabled
        if enable_sanitization and self.sanitizer:
            sanitized_messages: list[ChatMessage] = []
            for msg in request.messages:
                sanitized_content = self.sanitizer.sanitize(msg.content)
                sanitized_messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=sanitized_content,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            exec_request = request.model_copy(update={"messages": sanitized_messages})
        else:
            exec_request = request

        # Execute inference
        response = await provider.generate(exec_request)

        # Restore sanitized placeholders in the output
        if enable_sanitization and self.sanitizer and response.content:
            restored_content = self.sanitizer.restore(response.content)
            response = response.model_copy(update={"content": restored_content})

        return response
