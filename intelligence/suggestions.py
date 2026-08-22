"""Proactive Intelligence and Suggestion Engine."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from core.compat import BaseModel, Field


class SuggestionCategory(str, Enum):
    """Domains for proactive recommendations."""
    PROJECT_IMPROVEMENT = "project_improvement"
    STUDY_PLAN = "study_plan"
    TASK_PLAN = "task_plan"
    EMAIL_IMPROVEMENT = "email_improvement"
    RESEARCH_DIRECTION = "research_direction"
    PRODUCTIVITY = "productivity"
    GENERAL_IDEA = "general_idea"


class ProactiveSuggestion(BaseModel):
    """Structured proactive recommendation."""
    suggestion_id: UUID = Field(default_factory=uuid4)
    category: SuggestionCategory
    title: str
    rationale: str
    recommended_steps: list[str] = Field(default_factory=list)
    is_sensitive_action_required: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SuggestionEngine:
    """Evaluates project contexts to generate non-intrusive proactive suggestions."""

    def generate_project_suggestions(self, project_summary: str) -> list[ProactiveSuggestion]:
        """Generate architectural and workflow optimization ideas."""
        return [
            ProactiveSuggestion(
                category=SuggestionCategory.PROJECT_IMPROVEMENT,
                title="Integrate Hermetic Security Regression Testing",
                rationale="Automating prompt injection fuzzing in CI ensures safety guardrails cannot regress.",
                recommended_steps=[
                    "Add adversarial test cases to tests/security/",
                    "Configure pre-commit hook to verify test pass status",
                ],
                is_sensitive_action_required=False,
            )
        ]
