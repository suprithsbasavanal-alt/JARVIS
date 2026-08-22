"""Base Agent Interface and Execution States."""

from abc import ABC, abstractmethod
from enum import Enum
from core.context import SessionContext
from model_routing.schemas import ModelResponse


class AgentState(str, Enum):
    """Lifecycle states of an agent execution turn."""
    IDLE = "IDLE"
    PARSING_INTENT = "PARSING_INTENT"
    PLANNING = "PLANNING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING_TOOL = "EXECUTING_TOOL"
    VERIFYING_OUTPUT = "VERIFYING_OUTPUT"
    SYNTHESIZING_RESPONSE = "SYNTHESIZING_RESPONSE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class BaseAgent(ABC):
    """Abstract agent controller."""

    @abstractmethod
    async def process_turn(self, user_query: str, context: SessionContext) -> ModelResponse:
        """Execute single full conversation/reasoning turn."""
        pass
