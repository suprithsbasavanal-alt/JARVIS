"""Proactive Intelligence Coordinator for Phase 6.3."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import time
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from core.exceptions import (
    ProactiveCooldownActiveError,
    ProactiveTriggerError,
)
from intelligence.analyzer import DisagreementAssessment, ReasoningAnalyzer
from intelligence.plan_generator import PlanDifficulty, PlanGenerator, StructuredPlan
from intelligence.project_reviewer import (
    ProjectReviewEngine,
    ProjectReviewReport,
)
from intelligence.suggestions import (
    InformationalGuard,
    ProactiveSuggestion,
    SuggestionEngine,
    SuggestionPriority,
)
from security.audit_logger import AuditLogger


class TriggerType(str, Enum):
    """Event triggers that can initiate a proactive intelligence evaluation."""
    SESSION_START = "session_start"
    PROJECT_OPENED = "project_opened"
    PROPOSITION_SUBMITTED = "proposition_submitted"
    TASK_CREATED = "task_created"
    STUDY_REQUESTED = "study_requested"
    PERIODIC_CHECK = "periodic_check"
    MANUAL_REQUEST = "manual_request"


class ProactiveTrigger(BaseModel):
    """Contextual trigger payload initiating an informational evaluation."""
    trigger_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    trigger_type: TriggerType
    context_summary: str = ""
    project_path: str | None = None
    proposition: str | None = None
    topic: str | None = None
    goal: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProactiveEvaluationResult(BaseModel):
    """Aggregated, deduplicated proactive evaluation result with strict informational guard."""
    evaluation_id: UUID = Field(default_factory=uuid4)
    trigger: ProactiveTrigger
    review_report: ProjectReviewReport | None = None
    suggestions: list[ProactiveSuggestion] = Field(default_factory=list)
    disagreements: list[DisagreementAssessment] = Field(default_factory=list)
    generated_plans: list[StructuredPlan] = Field(default_factory=list)
    is_informational_only: bool = True
    evaluation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def format_summary(self) -> str:
        """Render a concise markdown representation of the evaluation result."""
        lines = [
            f"# Proactive Evaluation [{self.trigger.trigger_type.value.upper()}]",
            f"**Timestamp**: {self.evaluation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Informational Invariant**: Strictly Informational (Zero Direct Tool Execution)",
            "",
        ]

        if self.review_report:
            lines.extend([
                "## Project Review Summary",
                f"- **Health Score**: {self.review_report.health_score:.1f}/100.0",
                f"- **Findings Count**: {len(self.review_report.findings)}",
                "",
            ])

        if self.disagreements:
            lines.extend(["## Epistemic Observations & Disagreements"])
            for d in self.disagreements:
                if d.should_disagree:
                    lines.append(f"- **{d.category.value.upper()}**: {d.reason}")
            lines.append("")

        if self.suggestions:
            lines.extend(["## Proactive Recommendations"])
            for s in self.suggestions:
                lines.append(f"- **[{s.priority.value.upper()}] {s.title}**: {s.rationale}")
            lines.append("")

        if self.generated_plans:
            lines.extend(["## Generated Plans"])
            for p in self.generated_plans:
                lines.append(f"- **{p.title}** ({p.plan_type.value}, {len(p.steps)} steps)")
            lines.append("")

        lines.append("*(Note: Proactive advice requires explicit user command to execute any action.)*")
        return "\n".join(lines)


class ProactiveCoordinator:
    """Central orchestrator managing proactive intelligence, rate limiting, and deduplication."""

    def __init__(
        self,
        default_cooldown_seconds: float = 30.0,
        audit_logger: AuditLogger | None = None,
        project_reviewer: ProjectReviewEngine | None = None,
        plan_generator: PlanGenerator | None = None,
        reasoning_analyzer: ReasoningAnalyzer | None = None,
        suggestion_engine: SuggestionEngine | None = None,
    ) -> None:
        self.default_cooldown_seconds = default_cooldown_seconds
        self.audit_logger = audit_logger or AuditLogger()
        self.project_reviewer = project_reviewer or ProjectReviewEngine()
        self.plan_generator = plan_generator or PlanGenerator()
        self.reasoning_analyzer = reasoning_analyzer or ReasoningAnalyzer()
        self.suggestion_engine = suggestion_engine or SuggestionEngine()

        self._last_trigger_times: dict[TriggerType, float] = {}
        self._seen_suggestion_fingerprints: set[str] = set()

    def _compute_suggestion_fingerprint(self, suggestion: ProactiveSuggestion) -> str:
        """Compute deterministic SHA-256 fingerprint for recommendation deduplication."""
        raw = f"{suggestion.category.value}:{suggestion.title.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def evaluate_trigger(
        self,
        trigger: ProactiveTrigger,
        force: bool = False,
        min_priority: SuggestionPriority = SuggestionPriority.LOW,
    ) -> ProactiveEvaluationResult:
        """Process an event trigger, evaluate applicable proactive routines, and return structured result."""
        if not isinstance(trigger, ProactiveTrigger):
            raise ProactiveTriggerError("Trigger must be an instance of ProactiveTrigger.")

        now = time.monotonic()
        last_time = self._last_trigger_times.get(trigger.trigger_type, 0.0)

        # Enforce rate-limit cooldown unless forced or manual request
        if not force and trigger.trigger_type != TriggerType.MANUAL_REQUEST:
            if now - last_time < self.default_cooldown_seconds:
                remaining = self.default_cooldown_seconds - (now - last_time)
                raise ProactiveCooldownActiveError(
                    f"Proactive trigger '{trigger.trigger_type.value}' is on cooldown for another {remaining:.1f}s."
                )

        self._last_trigger_times[trigger.trigger_type] = now

        review_report: ProjectReviewReport | None = None
        disagreements: list[DisagreementAssessment] = []
        generated_plans: list[StructuredPlan] = []
        collected_suggestions: list[ProactiveSuggestion] = []

        # 1. Evaluate Project Review if path provided
        if trigger.project_path:
            review_report = self.project_reviewer.review_directory(
                directory_path=trigger.project_path,
                project_name="Workspace",
            )
            collected_suggestions.extend(review_report.proactive_suggestions)

        # 2. Evaluate Epistemic Reasoning Disagreement if proposition provided
        if trigger.proposition:
            assessment = self.reasoning_analyzer.evaluate_proposition(trigger.proposition)
            disagreements.append(assessment)

        # 3. Generate Study Plan if topic provided
        if trigger.topic:
            study_plan = self.plan_generator.generate_study_plan(topic=trigger.topic)
            generated_plans.append(study_plan)

        # 4. Generate Task Plan if goal provided
        if trigger.goal:
            task_plan = self.plan_generator.generate_task_plan(goal=trigger.goal)
            generated_plans.append(task_plan)

        # 5. Generate Contextual Suggestions from context_summary
        if trigger.context_summary:
            ctx_suggestions = self.suggestion_engine.generate_project_suggestions(trigger.context_summary)
            collected_suggestions.extend(ctx_suggestions)

        # Deduplicate suggestions across current batch and historical fingerprints
        filtered_suggestions: list[ProactiveSuggestion] = []
        for s in collected_suggestions:
            fp = self._compute_suggestion_fingerprint(s)
            if fp not in self._seen_suggestion_fingerprints:
                self._seen_suggestion_fingerprints.add(fp)
                filtered_suggestions.append(s)

        # Apply priority threshold filter
        final_suggestions = self.suggestion_engine.filter_by_priority(
            filtered_suggestions,
            min_priority=min_priority,
        )

        # Enforce strict informational-only safety invariant
        for s in final_suggestions:
            InformationalGuard.verify_no_unsolicited_execution(s, is_user_initiated=True)

        result = ProactiveEvaluationResult(
            trigger=trigger,
            review_report=review_report,
            suggestions=final_suggestions,
            disagreements=disagreements,
            generated_plans=generated_plans,
            is_informational_only=True,
        )

        # Log event in AuditLogger with SHA-256 chained integrity
        self.audit_logger.log(
            actor_id="proactive_coordinator",
            session_id="proactive_session",
            event_type="PROACTIVE_EVALUATION_COMPLETED",
            action_type=trigger.trigger_type.value,
            risk_level="LOW",
            target_resource=trigger.project_path or trigger.trigger_type.value,
            parameters={
                "trigger_id": trigger.trigger_id,
                "suggestions_count": len(final_suggestions),
                "disagreements_count": len(disagreements),
                "plans_count": len(generated_plans),
                "has_review_report": review_report is not None,
            },
            decision="SUCCESS",
        )

        return result

    def reset_cooldowns(self) -> None:
        """Reset trigger cooldown timestamps (useful for testing or session reset)."""
        self._last_trigger_times.clear()

    def clear_suggestion_history(self) -> None:
        """Clear seen suggestion fingerprints (useful for test isolation)."""
        self._seen_suggestion_fingerprints.clear()
