"""Abstract Base Classes for Agent Orchestrator."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class AgentTask(BaseModel):
    """Task definition submitted to the agent orchestrator."""
    task_id: str
    user_query: str
    session_id: str
    context: Dict[str, Any] = {}


class AgentExecutionResult(BaseModel):
    """Final output produced by the agent execution loop."""
    task_id: str
    final_output: str
    steps_taken: List[Dict[str, Any]]
    success: bool


class BaseAgentOrchestrator(ABC):
    """Abstract Port for Agent Reasoning Loop (ReAct / Plan-and-Solve)."""

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> AgentExecutionResult:
        """Executes a user task autonomously through reasoning, memory, and tool invocation."""
        pass
