"""Abstract Base Classes for AI Model Providers (DIP / OCP)."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel


class LLMRequest(BaseModel):
    """Normalized payload for LLM inference requests."""
    prompt: str
    system_instruction: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    stop_sequences: Optional[List[str]] = None


class LLMResponse(BaseModel):
    """Normalized response structure from LLM providers."""
    content: str
    raw_response: Dict[str, Any]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None


class BaseLLMProvider(ABC):
    """Abstract Port for Large Language Model vendors."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the LLM provider (e.g., 'openai', 'gemini')."""
        pass

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates a synchronous text/tool completion response."""
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Streams text tokens asynchronously."""
        pass
