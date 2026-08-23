"""Structured Study and Task Plan Generator for Phase 6.2."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from core.exceptions import PlanGenerationError


class PlanDifficulty(str, Enum):
    """Complexity level for generated study or task plans."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PlanType(str, Enum):
    """Categorization of structured plans."""
    STUDY_CURRICULUM = "study_curriculum"
    TASK_EXECUTION = "task_execution"
    SECURITY_AUDIT = "security_audit"
    ARCHITECTURE_MIGRATION = "architecture_migration"
    RESEARCH_ROADMAP = "research_roadmap"


class PlanMilestone(BaseModel):
    """High-level phase or checkpoint in a plan."""
    milestone_id: int
    title: str
    objective: str
    estimated_hours: float = 0.0


class PlanStepItem(BaseModel):
    """Granular, sequential action item within a milestone."""
    step_number: int
    milestone_id: int
    title: str
    description: str
    estimated_minutes: int = 60
    resources_or_tools: list[str] = Field(default_factory=list)
    deliverable: str
    is_actionable: bool = True


class StructuredPlan(BaseModel):
    """Structured, modular, trackable plan with strict informational boundaries."""
    plan_id: UUID = Field(default_factory=uuid4)
    title: str
    goal: str
    plan_type: PlanType
    difficulty: PlanDifficulty = PlanDifficulty.INTERMEDIATE
    estimated_duration: str
    prerequisites: list[str] = Field(default_factory=list)
    milestones: list[PlanMilestone] = Field(default_factory=list)
    steps: list[PlanStepItem] = Field(default_factory=list)
    risks_and_mitigations: list[dict[str, str]] = Field(default_factory=list)
    is_informational_only: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def format_markdown(self) -> str:
        """Render the structured plan in human-readable Markdown format."""
        lines = [
            f"# {self.title}",
            f"**Plan Type**: {self.plan_type.value.replace('_', ' ').title()} | **Difficulty**: {self.difficulty.value.title()}",
            f"**Goal**: {self.goal}",
            f"**Estimated Duration**: {self.estimated_duration}",
            "",
            "## Prerequisites",
        ]
        if self.prerequisites:
            for p in self.prerequisites:
                lines.append(f"- {p}")
        else:
            lines.append("- None")

        lines.extend(["", "## Milestones & Schedule"])
        for m in self.milestones:
            lines.extend([
                f"### Milestone {m.milestone_id}: {m.title} (~{m.estimated_hours:.1f} hours)",
                f"**Objective**: {m.objective}",
                "",
                "**Action Items**:",
            ])
            matching_steps = [s for s in self.steps if s.milestone_id == m.milestone_id]
            for s in matching_steps:
                lines.append(
                    f"- [ ] **Step {s.step_number}**: {s.title} ({s.estimated_minutes} min)\n"
                    f"      - *Description*: {s.description}\n"
                    f"      - *Deliverable*: `{s.deliverable}`"
                )
            lines.append("")

        if self.risks_and_mitigations:
            lines.extend(["## Risk Analysis & Mitigations"])
            for rm in self.risks_and_mitigations:
                risk = rm.get("risk", "Unknown risk")
                mitigation = rm.get("mitigation", "Standard monitoring")
                lines.append(f"- **Risk**: {risk} → **Mitigation**: {mitigation}")

        lines.extend([
            "",
            "---",
            "*Note: This plan is an informational recommendation. Execute steps explicitly through user direction.*",
        ])

        return "\n".join(lines)


class PlanGenerator:
    """Generates structured learning curricula, task workflows, and migration roadmaps."""

    def generate_study_plan(
        self,
        topic: str,
        target_level: PlanDifficulty = PlanDifficulty.INTERMEDIATE,
        duration_weeks: int = 4,
    ) -> StructuredPlan:
        """Generate a structured, milestone-based learning curriculum."""
        if not topic or not isinstance(topic, str) or not topic.strip():
            raise PlanGenerationError("Topic must be a non-empty string.")

        clean_topic = topic.strip()
        title = f"{clean_topic} Mastery Curriculum ({target_level.value.title()})"
        goal = f"Gain practical, production-ready proficiency in {clean_topic} across {duration_weeks} weeks."

        milestones = [
            PlanMilestone(
                milestone_id=1,
                title="Foundational Concepts & Core Architecture",
                objective=f"Understand theoretical foundations and primary primitives of {clean_topic}.",
                estimated_hours=float(duration_weeks * 2.5),
            ),
            PlanMilestone(
                milestone_id=2,
                title="Applied Implementation & Hands-on Exercises",
                objective=f"Build working prototypes and solve common architectural problems with {clean_topic}.",
                estimated_hours=float(duration_weeks * 3.5),
            ),
            PlanMilestone(
                milestone_id=3,
                title="Advanced Optimization & Security Hardening",
                objective=f"Master performance tuning, failure recovery, and secure production patterns in {clean_topic}.",
                estimated_hours=float(duration_weeks * 2.0),
            ),
        ]

        steps = [
            PlanStepItem(
                step_number=1,
                milestone_id=1,
                title=f"Review Official Documentation and Specifications for {clean_topic}",
                description=f"Read primary specifications, architecture whitepapers, and core design principles.",
                estimated_minutes=120,
                resources_or_tools=["Official Documentation", "Architecture RFCs"],
                deliverable="Annotated notes summarizing core concepts",
            ),
            PlanStepItem(
                step_number=2,
                milestone_id=1,
                title="Establish Local Development and Experimentation Sandbox",
                description="Set up isolated development environment with linting, typing, and test runner.",
                estimated_minutes=60,
                resources_or_tools=["Python 3.12 / Rust / TypeScript", "Local IDE"],
                deliverable="Functional development sandbox repository",
            ),
            PlanStepItem(
                step_number=3,
                milestone_id=2,
                title="Implement Core Modular Primitives",
                description=f"Write clean, strongly-typed components demonstrating core features of {clean_topic}.",
                estimated_minutes=180,
                resources_or_tools=["Type annotations", "Pydantic / Dataclasses"],
                deliverable="Tested implementation modules",
            ),
            PlanStepItem(
                step_number=4,
                milestone_id=2,
                title="Author Automated Regression Test Suite",
                description="Write unit and integration tests covering normal, edge-case, and error scenarios.",
                estimated_minutes=120,
                resources_or_tools=["pytest / unittest standard library"],
                deliverable="100% passing test suite",
            ),
            PlanStepItem(
                step_number=5,
                milestone_id=3,
                title="Perform Threat Modeling and Security Review",
                description="Identify potential attack surfaces, input injection risks, and fail-closed policies.",
                estimated_minutes=90,
                resources_or_tools=["Security Checklist", "STRIDE Threat Model"],
                deliverable="Security audit matrix",
            ),
        ]

        prerequisites = [
            "Familiarity with modern software design patterns",
            "Working knowledge of strongly-typed programming environments",
        ]

        risks_and_mitigations = [
            {
                "risk": "Time constraints impacting deep-dive exercises",
                "mitigation": "Focus on Milestones 1 and 2 first before advancing to deep optimizations.",
            },
            {
                "risk": "Outdated tutorial resources online",
                "mitigation": "Rely strictly on official documentation and verified source repositories.",
            },
        ]

        return StructuredPlan(
            title=title,
            goal=goal,
            plan_type=PlanType.STUDY_CURRICULUM,
            difficulty=target_level,
            estimated_duration=f"{duration_weeks} weeks (~{duration_weeks * 8} total study hours)",
            prerequisites=prerequisites,
            milestones=milestones,
            steps=steps,
            risks_and_mitigations=risks_and_mitigations,
            is_informational_only=True,
        )

    def generate_task_plan(
        self,
        goal: str,
        scope: str = "feature_development",
        difficulty: PlanDifficulty = PlanDifficulty.INTERMEDIATE,
    ) -> StructuredPlan:
        """Generate a modular, step-by-step task execution roadmap."""
        if not goal or not isinstance(goal, str) or not goal.strip():
            raise PlanGenerationError("Goal must be a non-empty string.")

        clean_goal = goal.strip()
        title = f"Task Execution Plan: {clean_goal[:60]}"

        milestones = [
            PlanMilestone(
                milestone_id=1,
                title="Requirements & Architectural Design",
                objective="Define interfaces, invariants, error handling, and test strategy.",
                estimated_hours=2.0,
            ),
            PlanMilestone(
                milestone_id=2,
                title="Implementation & Unit Verification",
                objective="Write modular components and hermetic unit tests.",
                estimated_hours=4.0,
            ),
            PlanMilestone(
                milestone_id=3,
                title="Security Review & Documentation",
                objective="Verify fail-closed security policies and author comprehensive documentation.",
                estimated_hours=2.0,
            ),
        ]

        steps = [
            PlanStepItem(
                step_number=1,
                milestone_id=1,
                title="Define Component Contracts and Types",
                description="Draft abstract base classes, Pydantic schemas, and exception hierarchies.",
                estimated_minutes=60,
                resources_or_tools=["Architecture Docs", "Type Checker"],
                deliverable="Typed module contracts",
            ),
            PlanStepItem(
                step_number=2,
                milestone_id=2,
                title="Implement Core Logic and Handlers",
                description="Implement deterministic algorithms conforming to abstract contracts.",
                estimated_minutes=120,
                resources_or_tools=["Local Python Runtime"],
                deliverable="Source implementation files",
            ),
            PlanStepItem(
                step_number=3,
                milestone_id=2,
                title="Execute Comprehensive Unit Test Suite",
                description="Ensure all unit and regression tests pass without mock leakage.",
                estimated_minutes=60,
                resources_or_tools=["unittest standard library"],
                deliverable="100% passing test report",
            ),
            PlanStepItem(
                step_number=4,
                milestone_id=3,
                title="Document Architecture and Add Decision Record",
                description="Update technical documentation and add Architecture Decision Record (ADR).",
                estimated_minutes=45,
                resources_or_tools=["Markdown Documentation"],
                deliverable="Updated docs/ and ADR entries",
            ),
        ]

        return StructuredPlan(
            title=title,
            goal=clean_goal,
            plan_type=PlanType.TASK_EXECUTION,
            difficulty=difficulty,
            estimated_duration="8.0 hours",
            prerequisites=["Access to repository workspace", "Clean working branch"],
            milestones=milestones,
            steps=steps,
            risks_and_mitigations=[
                {
                    "risk": "Interface regressions with existing subsystems",
                    "mitigation": "Run complete repository regression test suite after each milestone.",
                }
            ],
            is_informational_only=True,
        )
