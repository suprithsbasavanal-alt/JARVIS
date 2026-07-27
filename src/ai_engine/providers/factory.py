"""Model Provider Factory (SOLID - Factory Pattern / OCP)."""

from typing import Dict, Type
from src.ai_engine.contracts.provider import BaseLLMProvider
from src.ai_engine.providers.openai_provider import OpenAIProvider
from src.ai_engine.providers.gemini_provider import GeminiProvider
from src.ai_engine.providers.mock_provider import MockLLMProvider
from src.shared.exceptions.base import ConfigurationError
from config.settings import settings


class LLMProviderFactory:
    """Factory creating LLMProvider instances based on configuration."""

    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "mock": MockLLMProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseLLMProvider]) -> None:
        """Dynamically registers a new LLM provider type (OCP)."""
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def get_provider(cls, provider_name: str = None) -> BaseLLMProvider:
        """Instantiates and returns target LLMProvider adapter."""
        target_name = (provider_name or settings.model.default_provider).lower()
        if target_name not in cls._registry:
            # Fallback to mock provider if unknown
            return MockLLMProvider()

        provider_cls = cls._registry[target_name]
        return provider_cls()
