"""Task Planner and Intent Decomposer."""

from core.compat import BaseModel, Field


class PlanStep(BaseModel):
    """Individual atomic step in an execution plan."""
    step_number: int
    description: str
    tool_name: str | None = None
    is_sensitive: bool = False


class ExecutionPlan(BaseModel):
    """Structured multi-step task plan."""
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    requires_human_approval: bool = False


class TaskPlanner:
    """Decomposes complex requests into verified execution plans."""

    def create_plan(self, goal: str, available_tools: list[str]) -> ExecutionPlan:
        """Construct deterministic execution plan."""
        # Simple single-step plan default in Phase 0 scaffolding
        return ExecutionPlan(
            goal=goal,
            steps=[PlanStep(step_number=1, description=f"Analyze and fulfill: {goal}")],
            requires_human_approval=False,
        )
