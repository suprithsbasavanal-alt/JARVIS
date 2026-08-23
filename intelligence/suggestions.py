"""Proactive Intelligence and Suggestion Engine with Strict Informational Guards."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from core.exceptions import ProactiveActionExecutionBlockedError


class SuggestionCategory(str, Enum):
    """Domains for proactive recommendations."""
    PROJECT_IMPROVEMENT = "project_improvement"
    SECURITY_HARDENING = "security_hardening"
    STUDY_PLAN = "study_plan"
    TASK_PLAN = "task_plan"
    CODE_QUALITY = "code_quality"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    PRODUCTIVITY = "productivity"
    GENERAL_IDEA = "general_idea"


class SuggestionPriority(str, Enum):
    """Urgency and impact of a proactive recommendation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProactiveSuggestion(BaseModel):
    """Structured proactive recommendation with strict informational boundaries."""
    suggestion_id: UUID = Field(default_factory=uuid4)
    category: SuggestionCategory
    priority: SuggestionPriority = SuggestionPriority.MEDIUM
    title: str
    rationale: str
    recommended_steps: list[str] = Field(default_factory=list)
    is_sensitive_action_required: bool = False
    is_informational_only: bool = True
    is_executable_directly: bool = False
    source_subsystem: str = "proactive_engine"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def format_display(self) -> str:
        """Format the proactive recommendation for safe user presentation."""
        steps_str = "\n".join(f"  {idx + 1}. {step}" for idx, step in enumerate(self.recommended_steps))
        return (
            f"[PROACTIVE SUGGESTION] [{self.category.value.upper()}] ({self.priority.value.upper()})\n"
            f"Title: {self.title}\n"
            f"Rationale: {self.rationale}\n"
            f"Recommended Next Steps:\n{steps_str}\n"
            f"(Note: Informational suggestion. Requires explicit user command to execute.)"
        )


class InformationalGuard:
    """Enforces the Phase 6 constraint that suggestions must never automatically execute tools."""

    @staticmethod
    def verify_no_unsolicited_execution(suggestion: ProactiveSuggestion, is_user_initiated: bool = False) -> None:
        """Reject any automated attempt to execute a proactive suggestion directly."""
        if not is_user_initiated:
            raise ProactiveActionExecutionBlockedError(
                f"Automatic execution of proactive suggestion '{suggestion.title}' blocked. "
                "Proactive suggestions are informational only and require an explicit user command."
            )


class SuggestionEngine:
    """Evaluates project and dialogue contexts to generate non-intrusive proactive suggestions."""

    PRIORITY_WEIGHTS = {
        SuggestionPriority.LOW: 1,
        SuggestionPriority.MEDIUM: 2,
        SuggestionPriority.HIGH: 3,
        SuggestionPriority.CRITICAL: 4,
    }

    def generate_project_suggestions(self, project_summary: str) -> list[ProactiveSuggestion]:
        """Generate architectural, testing, and workflow optimization ideas."""
        suggestions: list[ProactiveSuggestion] = []
        summary_lower = (project_summary or "").lower()

        if "security" in summary_lower or "auth" in summary_lower:
            suggestions.append(
                ProactiveSuggestion(
                    category=SuggestionCategory.SECURITY_HARDENING,
                    priority=SuggestionPriority.HIGH,
                    title="Audit Security Regression Boundaries",
                    rationale="Regularly auditing permission boundaries and cryptographic keys prevents privilege escalation.",
                    recommended_steps=[
                        "Review permission engine matrix across all tool definitions",
                        "Verify AEAD encryption keys remain properly abstracted",
                    ],
                    is_sensitive_action_required=False,
                )
            )

        if "test" in summary_lower or "coverage" in summary_lower:
            suggestions.append(
                ProactiveSuggestion(
                    category=SuggestionCategory.TESTING,
                    priority=SuggestionPriority.MEDIUM,
                    title="Expand Property-Based and Fuzz Testing",
                    rationale="Property-based testing identifies edge-case payload crashes before deployment.",
                    recommended_steps=[
                        "Add malformed input fuzz tests to parser endpoints",
                        "Verify timeout handlers trigger cleanly under heavy load",
                    ],
                    is_sensitive_action_required=False,
                )
            )

        # Default recommendation if general query
        if not suggestions:
            suggestions.append(
                ProactiveSuggestion(
                    category=SuggestionCategory.PROJECT_IMPROVEMENT,
                    priority=SuggestionPriority.LOW,
                    title="Establish Continuous Integration Verification",
                    rationale="Running complete hermetic test suites on commit prevents silent regressions.",
                    recommended_steps=[
                        "Configure pre-commit unit test runner",
                        "Verify static type checking with mypy strict mode",
                    ],
                    is_sensitive_action_required=False,
                )
            )

        return suggestions

    def filter_by_priority(
        self,
        suggestions: list[ProactiveSuggestion],
        min_priority: SuggestionPriority = SuggestionPriority.MEDIUM,
    ) -> list[ProactiveSuggestion]:
        """Filter suggestions by minimum priority threshold."""
        min_weight = self.PRIORITY_WEIGHTS.get(min_priority, 2)
        return [
            s for s in suggestions
            if self.PRIORITY_WEIGHTS.get(s.priority, 1) >= min_weight
        ]
