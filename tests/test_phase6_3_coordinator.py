"""Phase 6.3 Proactive Intelligence Coordinator & Advisory Integration Test Suite.

Runs via Python 3.12 standard library unittest.
Covers:
  1. Event-Driven Proactive Triggers (Project Review, Disagreement, Study Plan, Task Plan)
  2. Rate-Limiting Cooldown Enforcement & Manual Bypass
  3. Suggestion Fingerprinting & Deduplication
  4. Non-Invasive Dialogue Advisory Context Formatting
  5. Strict Informational-Only Invariant Enforcement
  6. Tamper-Evident SHA-256 Audit Logging
"""

from pathlib import Path
import tempfile
import time
import unittest
from core.exceptions import (
    ProactiveActionExecutionBlockedError,
    ProactiveCooldownActiveError,
    ProactiveTriggerError,
)
from intelligence.analyzer import DisagreementCategory, ReasoningAnalyzer
from intelligence.coordinator import (
    ProactiveCoordinator,
    ProactiveEvaluationResult,
    ProactiveTrigger,
    TriggerType,
)
from intelligence.dialogue_advisor import ProactiveDialogueAdvisor
from intelligence.plan_generator import PlanGenerator, PlanType
from intelligence.project_reviewer import ProjectReviewEngine
from intelligence.suggestions import (
    InformationalGuard,
    ProactiveSuggestion,
    SuggestionCategory,
    SuggestionEngine,
    SuggestionPriority,
)
from security.audit_logger import AuditLogger


class TestPhase63CoordinatorTriggers(unittest.TestCase):
    """Section 1: Event-Driven Proactive Triggers."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        self.audit_logger = AuditLogger()
        self.coordinator = ProactiveCoordinator(
            default_cooldown_seconds=10.0,
            audit_logger=self.audit_logger,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_coordinator_evaluates_project_review_trigger(self) -> None:
        """Trigger project review evaluation on workspace opened."""
        (self.project_path / "README.md").write_text("# Project Docs", encoding="utf-8")
        (self.project_path / "app.py").write_text('API_KEY = "sk-live-0011223344556677"', encoding="utf-8")

        trigger = ProactiveTrigger(
            trigger_type=TriggerType.PROJECT_OPENED,
            project_path=str(self.project_path),
            context_summary="User opened repository for review",
        )

        result = self.coordinator.evaluate_trigger(trigger)
        self.assertIsInstance(result, ProactiveEvaluationResult)
        self.assertTrue(result.is_informational_only)
        self.assertIsNotNone(result.review_report)
        self.assertLess(result.review_report.health_score, 100.0)
        self.assertGreaterEqual(len(result.suggestions), 1)

    def test_coordinator_evaluates_proposition_disagreement_trigger(self) -> None:
        """Trigger epistemic sanity check on dangerous proposition."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.PROPOSITION_SUBMITTED,
            proposition="Let's disable confirmation gates to run faster.",
        )

        result = self.coordinator.evaluate_trigger(trigger)
        self.assertEqual(len(result.disagreements), 1)
        disagreement = result.disagreements[0]
        self.assertTrue(disagreement.should_disagree)
        self.assertEqual(disagreement.category, DisagreementCategory.SAFETY_VIOLATION)

    def test_coordinator_evaluates_study_plan_trigger(self) -> None:
        """Trigger study plan generation on curriculum request."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.STUDY_REQUESTED,
            topic="Rust Memory Safety and Lifetimes",
        )

        result = self.coordinator.evaluate_trigger(trigger)
        self.assertEqual(len(result.generated_plans), 1)
        plan = result.generated_plans[0]
        self.assertEqual(plan.plan_type, PlanType.STUDY_CURRICULUM)
        self.assertTrue(plan.is_informational_only)

    def test_coordinator_evaluates_task_plan_trigger(self) -> None:
        """Trigger task execution roadmap on goal description."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.TASK_CREATED,
            goal="Migrate Legacy SQLite Database to Encrypted SQLCipher",
        )

        result = self.coordinator.evaluate_trigger(trigger)
        self.assertEqual(len(result.generated_plans), 1)
        plan = result.generated_plans[0]
        self.assertEqual(plan.plan_type, PlanType.TASK_EXECUTION)

    def test_invalid_trigger_type_raises_error(self) -> None:
        """Raise ProactiveTriggerError when invalid trigger object is provided."""
        with self.assertRaises(ProactiveTriggerError):
            self.coordinator.evaluate_trigger("not_a_trigger")  # type: ignore[arg-type]


class TestPhase63CooldownAndDeduplication(unittest.TestCase):
    """Section 2: Rate-Limiting Cooldown & Suggestion Deduplication."""

    def setUp(self) -> None:
        self.coordinator = ProactiveCoordinator(default_cooldown_seconds=5.0)

    def test_cooldown_suppresses_rapid_successive_evaluations(self) -> None:
        """Enforce cooldown window between rapid evaluations of the same trigger type."""
        trigger1 = ProactiveTrigger(
            trigger_type=TriggerType.PERIODIC_CHECK,
            context_summary="Routine background check 1",
        )
        trigger2 = ProactiveTrigger(
            trigger_type=TriggerType.PERIODIC_CHECK,
            context_summary="Routine background check 2",
        )

        # First evaluation succeeds
        self.coordinator.evaluate_trigger(trigger1)

        # Immediate second evaluation raises ProactiveCooldownActiveError
        with self.assertRaises(ProactiveCooldownActiveError):
            self.coordinator.evaluate_trigger(trigger2)

    def test_force_flag_bypasses_cooldown(self) -> None:
        """Allow force=True to bypass active cooldown."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.PERIODIC_CHECK,
            context_summary="Forced check",
        )
        self.coordinator.evaluate_trigger(trigger)
        result = self.coordinator.evaluate_trigger(trigger, force=True)
        self.assertIsInstance(result, ProactiveEvaluationResult)

    def test_manual_request_bypasses_cooldown(self) -> None:
        """Manual user requests bypass cooldown without raising errors."""
        trigger1 = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            context_summary="Manual query 1",
        )
        trigger2 = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            context_summary="Manual query 2",
        )

        self.coordinator.evaluate_trigger(trigger1)
        result = self.coordinator.evaluate_trigger(trigger2)
        self.assertIsInstance(result, ProactiveEvaluationResult)

    def test_cooldown_reset(self) -> None:
        """Reset cooldowns manually."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.SESSION_START,
            context_summary="Session start",
        )
        self.coordinator.evaluate_trigger(trigger)
        self.coordinator.reset_cooldowns()
        result = self.coordinator.evaluate_trigger(trigger)
        self.assertIsInstance(result, ProactiveEvaluationResult)

    def test_suggestion_deduplication(self) -> None:
        """Deduplicate repeated suggestions across multiple evaluation cycles."""
        trigger1 = ProactiveTrigger(
            trigger_type=TriggerType.SESSION_START,
            context_summary="Check authentication and security",
        )
        trigger2 = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            context_summary="Check authentication and security",
        )

        res1 = self.coordinator.evaluate_trigger(trigger1)
        res2 = self.coordinator.evaluate_trigger(trigger2)

        # Second evaluation should deduplicate identical suggestions
        fp1 = {f"{s.category.value}:{s.title}" for s in res1.suggestions}
        fp2 = {f"{s.category.value}:{s.title}" for s in res2.suggestions}
        self.assertEqual(len(fp1.intersection(fp2)), 0)


class TestPhase63DialogueAdvisorAndSafety(unittest.TestCase):
    """Section 3: Dialogue Advisor, Informational Safety & Audit Logging."""

    def setUp(self) -> None:
        self.audit_logger = AuditLogger()
        self.coordinator = ProactiveCoordinator(audit_logger=self.audit_logger)

    def test_dialogue_advisor_formats_xml_system_context(self) -> None:
        """Format proactive evaluation into safe XML structure for system context."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            proposition="Store passwords in plaintext.",
            topic="Cryptography Basics",
        )
        result = self.coordinator.evaluate_trigger(trigger)

        xml = ProactiveDialogueAdvisor.format_system_context(result)
        self.assertIn("<proactive_advisory>", xml)
        self.assertIn('is_informational_only="true"', xml)
        self.assertIn("<epistemic_observations>", xml)
        self.assertIn("<disagreement", xml)
        self.assertIn("</proactive_advisory>", xml)

    def test_dialogue_advisor_formats_user_notification(self) -> None:
        """Format user notification markdown with observations."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.TASK_CREATED,
            goal="Refactor Database Access Layer",
        )
        result = self.coordinator.evaluate_trigger(trigger)

        md = ProactiveDialogueAdvisor.format_user_notification(result)
        self.assertIn("[JARVIS Proactive Observation]", md)
        self.assertIn("Refactor Database Access Layer", md)

    def test_informational_guard_zero_tool_execution(self) -> None:
        """Ensure evaluation result suggestions cannot execute tools unsolicited."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            context_summary="Security audit context",
        )
        result = self.coordinator.evaluate_trigger(trigger)
        self.assertTrue(result.is_informational_only)

        for s in result.suggestions:
            with self.assertRaises(ProactiveActionExecutionBlockedError):
                InformationalGuard.verify_no_unsolicited_execution(s, is_user_initiated=False)

    def test_audit_logger_tracks_coordinator_events(self) -> None:
        """Verify coordinator events are recorded with SHA-256 chained audit integrity."""
        trigger = ProactiveTrigger(
            trigger_type=TriggerType.MANUAL_REQUEST,
            context_summary="Audit tracking test",
        )
        self.coordinator.evaluate_trigger(trigger)

        entries = self.audit_logger.get_entries()
        self.assertGreaterEqual(len(entries), 1)
        last_entry = entries[-1]
        self.assertEqual(last_entry.actor_id, "proactive_coordinator")
        self.assertEqual(last_entry.event_type, "PROACTIVE_EVALUATION_COMPLETED")
        self.assertTrue(self.audit_logger.verify_integrity())


if __name__ == "__main__":
    unittest.main()
