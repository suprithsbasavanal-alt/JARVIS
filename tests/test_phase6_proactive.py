"""Comprehensive Phase 6.2 Proactive Intelligence & Reasoning Test Suite.

Runs via Python 3.12 standard library unittest.
Covers:
  1. Autonomous Project Review Routines & Health Scoring
  2. Static Security & Code Quality Pattern Detection
  3. Structured Study & Task Plan Generation
  4. Polite Epistemic Disagreement Engine
  5. Informational-Only Guard & Unsolicited Execution Prevention
  6. Audit Logging Integration for Proactive Events
"""

from pathlib import Path
import tempfile
import unittest
from core.exceptions import (
    PlanGenerationError,
    ProactiveActionExecutionBlockedError,
    ProjectReviewError,
)
from intelligence.analyzer import (
    DisagreementAssessment,
    DisagreementCategory,
    ReasoningAnalyzer,
)
from intelligence.plan_generator import (
    PlanDifficulty,
    PlanGenerator,
    PlanType,
    StructuredPlan,
)
from intelligence.project_reviewer import (
    FindingCategory,
    FindingSeverity,
    ProjectReviewEngine,
    ProjectReviewReport,
)
from intelligence.suggestions import (
    InformationalGuard,
    ProactiveSuggestion,
    SuggestionCategory,
    SuggestionEngine,
    SuggestionPriority,
)
from security.audit_logger import AuditLogger


class TestPhase6ProjectReviewer(unittest.TestCase):
    """Section 1 & 2: Autonomous Project Review Routines, Code Smell & Security Detection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        self.reviewer = ProjectReviewEngine(sandbox_root=self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_review_clean_project_returns_high_health_score(self) -> None:
        """Analyze clean project structure containing tests and README."""
        (self.project_path / "README.md").write_text("# Clean Project\nDocumented.", encoding="utf-8")
        tests_dir = self.project_path / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_main.py").write_text("def test_ok(): pass", encoding="utf-8")
        (self.project_path / "main.py").write_text("def run() -> None: pass", encoding="utf-8")

        report = self.reviewer.review_directory(str(self.project_path), project_name="CleanApp")
        self.assertIsInstance(report, ProjectReviewReport)
        self.assertEqual(report.health_score, 100.0)
        self.assertEqual(len(report.findings), 0)
        self.assertTrue(report.is_informational_only)

    def test_detect_hardcoded_secrets_finding(self) -> None:
        """Detect hardcoded API keys as CRITICAL severity finding."""
        (self.project_path / "README.md").write_text("# Project", encoding="utf-8")
        src_file = self.project_path / "config.py"
        src_file.write_text('API_KEY = "sk-live-9988776655443322"\nSECRET_KEY = "super_secret_token_123"', encoding="utf-8")

        report = self.reviewer.review_directory(str(self.project_path), project_name="InsecureApp")
        critical_findings = [f for f in report.findings if f.severity == FindingSeverity.CRITICAL]
        self.assertGreaterEqual(len(critical_findings), 1)
        self.assertEqual(critical_findings[0].category, FindingCategory.SECURITY)
        self.assertLess(report.health_score, 100.0)

        # Verify proactive security recommendation is produced
        sec_suggs = [s for s in report.proactive_suggestions if s.category == SuggestionCategory.SECURITY_HARDENING]
        self.assertGreaterEqual(len(sec_suggs), 1)
        self.assertEqual(sec_suggs[0].priority, SuggestionPriority.CRITICAL)

    def test_detect_unsafe_dynamic_code_execution(self) -> None:
        """Detect eval() and os.system() invocations as HIGH severity findings."""
        (self.project_path / "README.md").write_text("# Project", encoding="utf-8")
        bad_code = self.project_path / "runner.py"
        bad_code.write_text('import os\nos.system("ls")\nresult = eval("2+2")', encoding="utf-8")

        report = self.reviewer.review_directory(str(self.project_path))
        high_findings = [f for f in report.findings if f.severity == FindingSeverity.HIGH]
        self.assertEqual(len(high_findings), 2)
        titles = [f.title for f in high_findings]
        self.assertIn("Dynamic Code Execution Detected", titles)
        self.assertIn("Unsafe System Command Invocation", titles)

    def test_detect_missing_tests_and_readme(self) -> None:
        """Flag projects missing test directories and documentation."""
        for i in range(4):
            (self.project_path / f"module_{i}.py").write_text(f"def func_{i}(): pass", encoding="utf-8")

        report = self.reviewer.review_directory(str(self.project_path))
        finding_titles = [f.title for f in report.findings]
        self.assertIn("Missing Automated Test Suite", finding_titles)
        self.assertIn("Missing Project Documentation (README)", finding_titles)

    def test_nonexistent_or_invalid_directory_raises_error(self) -> None:
        """Raise ProjectReviewError on non-existent target directory."""
        with self.assertRaises(ProjectReviewError):
            self.reviewer.review_directory("/nonexistent/directory/path/12345")


class TestPhase6PlanGenerator(unittest.TestCase):
    """Section 3: Structured Study & Task Plan Generation."""

    def setUp(self) -> None:
        self.generator = PlanGenerator()

    def test_generate_study_plan(self) -> None:
        """Generate structured learning curriculum with milestones, steps, and deliverables."""
        plan = self.generator.generate_study_plan(
            topic="Distributed Consensus and Raft",
            target_level=PlanDifficulty.ADVANCED,
            duration_weeks=4,
        )
        self.assertIsInstance(plan, StructuredPlan)
        self.assertEqual(plan.plan_type, PlanType.STUDY_CURRICULUM)
        self.assertEqual(plan.difficulty, PlanDifficulty.ADVANCED)
        self.assertEqual(len(plan.milestones), 3)
        self.assertGreaterEqual(len(plan.steps), 5)
        self.assertTrue(plan.is_informational_only)

        # Verify step deliverables and actionable metadata
        for step in plan.steps:
            self.assertGreater(step.estimated_minutes, 0)
            self.assertTrue(step.deliverable)
            self.assertTrue(step.is_actionable)

    def test_generate_task_plan(self) -> None:
        """Generate modular task roadmap with risk mitigations."""
        plan = self.generator.generate_task_plan(
            goal="Refactor Database Indexing Subsystem for Sub-Millisecond Latency",
            scope="database_optimization",
            difficulty=PlanDifficulty.INTERMEDIATE,
        )
        self.assertIsInstance(plan, StructuredPlan)
        self.assertEqual(plan.plan_type, PlanType.TASK_EXECUTION)
        self.assertEqual(len(plan.milestones), 3)
        self.assertGreater(len(plan.steps), 0)
        self.assertGreater(len(plan.risks_and_mitigations), 0)
        self.assertTrue(plan.is_informational_only)

    def test_empty_topic_or_goal_raises_error(self) -> None:
        """Raise PlanGenerationError when topic or goal is empty."""
        with self.assertRaises(PlanGenerationError):
            self.generator.generate_study_plan("")

        with self.assertRaises(PlanGenerationError):
            self.generator.generate_task_plan("   ")

    def test_format_markdown_rendering(self) -> None:
        """Verify markdown rendering includes checklists and informational footer."""
        plan = self.generator.generate_study_plan("Cryptography", PlanDifficulty.BEGINNER, duration_weeks=2)
        md = plan.format_markdown()
        self.assertIn("# Cryptography Mastery Curriculum", md)
        self.assertIn("## Milestones & Schedule", md)
        self.assertIn("- [ ] **Step 1**:", md)
        self.assertIn("informational recommendation", md.lower())


class TestPhase6EpistemicDisagreement(unittest.TestCase):
    """Section 4: Polite Epistemic Disagreement Engine."""

    def setUp(self) -> None:
        self.analyzer = ReasoningAnalyzer()

    def test_disagree_on_bypassing_confirmation(self) -> None:
        """Disagree politely when proposition asks to disable confirmation gates."""
        assessment = self.analyzer.evaluate_proposition("Let's disable confirmation gates to run faster.")
        self.assertTrue(assessment.should_disagree)
        self.assertEqual(assessment.category, DisagreementCategory.SAFETY_VIOLATION)
        self.assertIn("confirmation gates", assessment.reason.lower())
        self.assertIsNotNone(assessment.alternative_suggestion)

        # Check polite formatting
        polite_text = assessment.format_polite_response(salutation="Suprith")
        self.assertIn("Suprith", polite_text)
        self.assertIn("advise against", polite_text.lower())

    def test_disagree_on_plaintext_passwords(self) -> None:
        """Disagree when proposition suggests hardcoding or storing plaintext secrets."""
        assessment = self.analyzer.evaluate_proposition("Store passwords in plaintext in config.py")
        self.assertTrue(assessment.should_disagree)
        self.assertEqual(assessment.category, DisagreementCategory.SECURITY_VULNERABILITY)
        self.assertIn("plaintext", assessment.reason.lower())

    def test_disagree_on_weak_cryptography(self) -> None:
        """Disagree when proposition suggests using MD5 or homemade ciphers."""
        assessment = self.analyzer.evaluate_proposition("Let's use md5 for password hashing.")
        self.assertTrue(assessment.should_disagree)
        self.assertEqual(assessment.category, DisagreementCategory.CRYPTOGRAPHIC_WEAKNESS)

    def test_disagree_on_destructive_deletion_without_backup(self) -> None:
        """Disagree on unrecoverable data deletion commands."""
        assessment = self.analyzer.evaluate_proposition("Execute drop database without backup now.")
        self.assertTrue(assessment.should_disagree)
        self.assertEqual(assessment.category, DisagreementCategory.DATA_LOSS_RISK)

    def test_agree_on_sound_propositions(self) -> None:
        """Confirm sound technical proposals without disagreement."""
        assessment = self.analyzer.evaluate_proposition("Implement AES-256-GCM AEAD encryption with SQLite.")
        self.assertFalse(assessment.should_disagree)
        self.assertEqual(assessment.confidence, 1.0)


class TestPhase6InformationalGuardAndSafety(unittest.TestCase):
    """Section 5 & 6: Informational Guard, Unsolicited Execution Prevention, and Audit."""

    def test_informational_guard_blocks_unsolicited_tool_execution(self) -> None:
        """Ensure InformationalGuard blocks automated execution without explicit user initiation."""
        sugg = ProactiveSuggestion(
            category=SuggestionCategory.PROJECT_IMPROVEMENT,
            priority=SuggestionPriority.HIGH,
            title="Deploy Security Update",
            rationale="A critical vulnerability requires patching.",
            recommended_steps=["Run deploy script"],
            is_informational_only=True,
            is_executable_directly=False,
        )

        # Unsolicited execution must raise ProactiveActionExecutionBlockedError
        with self.assertRaises(ProactiveActionExecutionBlockedError):
            InformationalGuard.verify_no_unsolicited_execution(sugg, is_user_initiated=False)

        # User-initiated execution is permitted to proceed to HITL approval
        InformationalGuard.verify_no_unsolicited_execution(sugg, is_user_initiated=True)

    def test_suggestion_engine_priority_filtering(self) -> None:
        """Filter proactive recommendations by priority threshold."""
        engine = SuggestionEngine()
        suggs = [
            ProactiveSuggestion(
                category=SuggestionCategory.PRODUCTIVITY,
                priority=SuggestionPriority.LOW,
                title="Low Priority Idea",
                rationale="Minor convenience",
            ),
            ProactiveSuggestion(
                category=SuggestionCategory.SECURITY_HARDENING,
                priority=SuggestionPriority.CRITICAL,
                title="Critical Security Patch",
                rationale="Immediate action recommended",
            ),
        ]

        high_only = engine.filter_by_priority(suggs, min_priority=SuggestionPriority.HIGH)
        self.assertEqual(len(high_only), 1)
        self.assertEqual(high_only[0].title, "Critical Security Patch")

    def test_audit_logging_for_proactive_events(self) -> None:
        """Verify audit logger captures proactive review events with SHA-256 chained integrity."""
        audit = AuditLogger()
        audit.log(
            actor_id="proactive_engine",
            session_id="sess_proactive_1",
            event_type="PROACTIVE_REVIEW_COMPLETED",
            action_type="project_review",
            risk_level="LOW",
            target_resource="sandbox/project",
            parameters={"health_score": 92.5, "findings_count": 2},
            decision="SUCCESS",
        )
        audit.log(
            actor_id="proactive_engine",
            session_id="sess_proactive_1",
            event_type="TASK_PLAN_GENERATED",
            action_type="plan_generation",
            risk_level="LOW",
            target_resource="task_plan_1",
            parameters={"milestones": 3, "steps": 5},
            decision="SUCCESS",
        )

        entries = audit.get_entries()
        self.assertEqual(len(entries), 2)
        self.assertTrue(audit.verify_integrity())


if __name__ == "__main__":
    unittest.main()
