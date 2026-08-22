"""Deterministic Mock Model Provider for Phase 0 Safe Development & Testing."""

from model_routing.base import BaseModelProvider
from model_routing.schemas import ModelRequest, ModelResponse, ToolCallDefinition


class MockModelProvider(BaseModelProvider):
    """Hermetic mock provider that produces controlled, safe responses for testing."""

    def __init__(self, provider_name: str = "mock-provider") -> None:
        super().__init__(provider_name)
        self.default_canned_response = "I am JARVIS, ready to assist."
        self.tool_triggers: dict[str, ToolCallDefinition] = {}

    def set_canned_response(self, text: str) -> None:
        """Configure mock text response."""
        self.default_canned_response = text

    def register_tool_trigger(self, trigger_keyword: str, tool_call: ToolCallDefinition) -> None:
        """Configure mock to return a tool call when a keyword appears in the user query."""
        self.tool_triggers[trigger_keyword.lower()] = tool_call

    async def generate(self, request: ModelRequest) -> ModelResponse:
        # Check last user message for triggers
        last_message = request.messages[-1].content.lower() if request.messages else ""

        for keyword, tool_call in self.tool_triggers.items():
            if keyword in last_message:
                return ModelResponse(
                    model_name="mock-model",
                    provider_name=self.provider_name,
                    content="",
                    tool_calls=[tool_call],
                    prompt_tokens=10,
                    completion_tokens=20,
                )

        return ModelResponse(
            model_name="mock-model",
            provider_name=self.provider_name,
            content=self.default_canned_response,
            prompt_tokens=10,
            completion_tokens=25,
        )

    async def is_healthy(self) -> bool:
        return True
