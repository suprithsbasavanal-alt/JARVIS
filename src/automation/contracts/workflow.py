"""Abstract Base Classes for Workflow Automation (DIP)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class WorkflowStep(BaseModel):
    """Step definition within a workflow DAG."""
    step_id: str
    action_name: str
    params: Dict[str, Any]
    depends_on: List[str] = []


class WorkflowDefinition(BaseModel):
    """Complete workflow definition schema."""
    workflow_id: str
    name: str
    steps: List[WorkflowStep]


class WorkflowEngineContract(ABC):
    """Abstract Interface for Executing Workflows."""

    @abstractmethod
    async def run_workflow(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Executes workflow DAG steps sequentially or in parallel based on dependencies."""
        pass
