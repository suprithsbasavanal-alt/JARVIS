"""Deterministic Mock Model Provider for Phase 1 Safe Development & Testing."""

from core.exceptions import ProviderUnavailableError
from model_routing.base import BaseModelProvider
from model_routing.schemas import ModelRequest, ModelResponse, ToolCallDefinition


class MockModelProvider(BaseModelProvider):
    """Hermetic mock provider that produces controlled, safe responses for testing."""

    def __init__(self, provider_name: str = "mock-provider", is_online: bool = True) -> None:
        super().__init__(provider_name)
        self.is_online = is_online
        self.default_canned_response = "I am JARVIS, ready to assist."
        self.tool_triggers: dict[str, ToolCallDefinition] = {}

    def set_canned_response(self, text: str) -> None:
        """Configure mock text response."""
        self.default_canned_response = text

    def set_online_status(self, online: bool) -> None:
        """Toggle online/offline status for fail-closed testing."""
        self.is_online = online

    def register_tool_trigger(self, trigger_keyword: str, tool_call: ToolCallDefinition) -> None:
        """Configure mock to return a tool call when a keyword appears in the user query."""
        self.tool_triggers[trigger_keyword.lower()] = tool_call

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not self.is_online:
            raise ProviderUnavailableError(f"Mock provider '{self.provider_name}' is currently offline.")

        # If previous turn had a tool response, synthesize tool result explanation
        for msg in request.messages:
            if msg.role.value == "tool":
                return ModelResponse(
                    model_name="mock-reasoning",
                    provider_name=self.provider_name,
                    content=f"Based on the tool results: {msg.content}",
                    prompt_tokens=30,
                    completion_tokens=20,
                )

        # Check last user message for triggers or proactive suggestions
        last_message = request.messages[-1].content.lower() if request.messages else ""

        # 1. Proactive suggestion triggers
        if "starting a project" in last_message or "college project" in last_message:
            return ModelResponse(
                model_name="mock-reasoning",
                provider_name=self.provider_name,
                content="I suggest creating a requirements document, task list, README, and test plan.",
                prompt_tokens=15,
                completion_tokens=25,
            )

        # 2. Tool call triggers
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

        # 3. Default canned response
        return ModelResponse(
            model_name="mock-model",
            provider_name=self.provider_name,
            content=self.default_canned_response,
            prompt_tokens=10,
            completion_tokens=25,
        )

    async def is_healthy(self) -> bool:
        return self.is_online
