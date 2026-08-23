"""Proactive Dialogue Advisory Integration for Phase 6.3."""

from intelligence.analyzer import DisagreementAssessment
from intelligence.coordinator import ProactiveEvaluationResult


class ProactiveDialogueAdvisor:
    """Formats proactive observations and evaluation results into safe, unobtrusive conversational context."""

    @staticmethod
    def format_system_context(evaluation: ProactiveEvaluationResult) -> str:
        """Format proactive evaluation into an inert XML-tagged data block for LLM system context."""
        lines = [
            "<proactive_advisory>",
            f'  <metadata trigger="{evaluation.trigger.trigger_type.value}" is_informational_only="true" />',
        ]

        if evaluation.review_report:
            lines.extend([
                "  <project_health>",
                f"    <score>{evaluation.review_report.health_score:.1f}</score>",
                f"    <findings_count>{len(evaluation.review_report.findings)}</findings_count>",
                "  </project_health>",
            ])

        if evaluation.disagreements:
            lines.append("  <epistemic_observations>")
            for d in evaluation.disagreements:
                if d.should_disagree:
                    lines.append(
                        f'    <disagreement category="{d.category.value}">\n'
                        f"      <reason>{d.reason}</reason>\n"
                        f"      <alternative>{d.alternative_suggestion}</alternative>\n"
                        f"    </disagreement>"
                    )
            lines.append("  </epistemic_observations>")

        if evaluation.suggestions:
            lines.append("  <recommendations>")
            for s in evaluation.suggestions:
                lines.append(
                    f'    <suggestion category="{s.category.value}" priority="{s.priority.value}">\n'
                    f"      <title>{s.title}</title>\n"
                    f"      <rationale>{s.rationale}</rationale>\n"
                    f"    </suggestion>"
                )
            lines.append("  </recommendations>")

        if evaluation.generated_plans:
            lines.append("  <plans>")
            for p in evaluation.generated_plans:
                lines.append(
                    f'    <plan title="{p.title}" type="{p.plan_type.value}" steps="{len(p.steps)}" />'
                )
            lines.append("  </plans>")

        lines.extend([
            "  <!-- Informational only: Do not execute any tool or command without explicit user direction -->",
            "</proactive_advisory>",
        ])

        return "\n".join(lines)

    @staticmethod
    def format_user_notification(evaluation: ProactiveEvaluationResult) -> str:
        """Format proactive evaluation as an elegant markdown notification for the user."""
        lines = [
            f"**[JARVIS Proactive Observation]** (Trigger: *{evaluation.trigger.trigger_type.value}*)",
        ]

        if evaluation.review_report:
            lines.append(
                f"- **Project Health**: {evaluation.review_report.health_score:.1f}/100.0 "
                f"({len(evaluation.review_report.findings)} findings discovered)"
            )

        for d in evaluation.disagreements:
            if d.should_disagree:
                lines.append(f"- **Note**: {d.polite_counter_argument}")

        for s in evaluation.suggestions:
            lines.append(f"- **Suggestion** ({s.priority.value.upper()}): {s.title} — {s.rationale}")

        for p in evaluation.generated_plans:
            lines.append(f"- **Plan Prepared**: {p.title} ({len(p.steps)} action items ready for review)")

        return "\n".join(lines)

    @staticmethod
    def format_disagreement_warning(assessment: DisagreementAssessment, salutation: str = "Sir") -> str:
        """Render polite epistemic disagreement warning."""
        return assessment.format_polite_response(salutation=salutation)
