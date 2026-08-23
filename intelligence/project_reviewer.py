"""Autonomous Project Review Engine for Phase 6.2 and 6.4 Resource Hardening."""

from datetime import datetime, timezone
from enum import Enum
import os
from pathlib import Path
import re
from uuid import uuid4
from core.compat import BaseModel, Field
from core.exceptions import ProjectReviewError, SandboxViolationError
from intelligence.suggestions import ProactiveSuggestion, SuggestionCategory, SuggestionPriority


class FindingSeverity(str, Enum):
    """Severity classification for project review findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(str, Enum):
    """Categorization for static analysis and architectural review findings."""
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


class ProjectFinding(BaseModel):
    """Individual finding identified during autonomous project review."""
    finding_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    title: str
    category: FindingCategory
    severity: FindingSeverity
    file_path: str
    line_number: int | None = None
    description: str
    remediation: str


class ProjectReviewReport(BaseModel):
    """Structured report produced by the autonomous project reviewer."""
    project_name: str
    review_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    summary: str
    files_analyzed_count: int = 0
    findings: list[ProjectFinding] = Field(default_factory=list)
    proactive_suggestions: list[ProactiveSuggestion] = Field(default_factory=list)
    is_informational_only: bool = True

    def format_markdown_report(self) -> str:
        """Format the review report as a structured Markdown document."""
        lines = [
            f"# Project Review Report: {self.project_name}",
            f"**Review Timestamp**: {self.review_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Health Score**: {self.health_score:.1f} / 100.0",
            f"**Files Analyzed**: {self.files_analyzed_count}",
            "",
            "## Summary",
            self.summary,
            "",
            f"## Findings ({len(self.findings)})",
        ]

        if not self.findings:
            lines.append("No critical findings or code smells detected. Project structure appears clean.")
        else:
            for f in self.findings:
                loc = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
                lines.extend([
                    f"### [{f.severity.value.upper()}] {f.title}",
                    f"- **Category**: {f.category.value}",
                    f"- **Location**: `{loc}`",
                    f"- **Description**: {f.description}",
                    f"- **Remediation**: {f.remediation}",
                    "",
                ])

        lines.extend([
            f"## Proactive Recommendations ({len(self.proactive_suggestions)})",
        ])
        for s in self.proactive_suggestions:
            lines.append(f"- **{s.title}** ({s.priority.value.upper()}): {s.rationale}")

        return "\n".join(lines)


class ProjectReviewEngine:
    """Performs static analysis, architectural health reviews, and resource-bounded scanning on project directories."""

    SEVERITY_DEDUCTIONS = {
        FindingSeverity.CRITICAL: 25.0,
        FindingSeverity.HIGH: 15.0,
        FindingSeverity.MEDIUM: 8.0,
        FindingSeverity.LOW: 3.0,
        FindingSeverity.INFO: 1.0,
    }

    # Static pattern rules for detecting code quality and security risks
    _SECURITY_PATTERNS = [
        (
            re.compile(r'(?i)(api[_-]?key|secret[_-]?key|password|auth[_-]?token)\s*=\s*["\'][a-zA-Z0-9_\-]{8,}["\']'),
            "Potential Hardcoded Secret or API Key",
            FindingCategory.SECURITY,
            FindingSeverity.CRITICAL,
            "A potential secret or credential is hardcoded directly in source code.",
            "Move credentials to environment variables or the OS Keyring/SecretVault.",
        ),
        (
            re.compile(r'\b(eval|exec)\s*\('),
            "Dynamic Code Execution Detected",
            FindingCategory.SECURITY,
            FindingSeverity.HIGH,
            "Use of dynamic evaluation (eval/exec) exposes the application to arbitrary code execution.",
            "Refactor code to use safe declarative schemas or ast.literal_eval.",
        ),
        (
            re.compile(r'\bos\.system\s*\('),
            "Unsafe System Command Invocation",
            FindingCategory.SECURITY,
            FindingSeverity.HIGH,
            "Direct os.system execution bypasses process sandboxing and input validation.",
            "Use ProcessSandboxExecutor with explicit argument lists instead.",
        ),
        (
            re.compile(r'\bhashlib\.(md5|sha1)\s*\('),
            "Obsolete Cryptographic Hash Function",
            FindingCategory.SECURITY,
            FindingSeverity.MEDIUM,
            "MD5 and SHA1 are cryptographically broken and vulnerable to collision attacks.",
            "Upgrade to SHA-256 or standard authenticated encryption (AES-256-GCM).",
        ),
        (
            re.compile(r'except\s*Exception\s*:\s*pass\b'),
            "Silent Exception Suppression (Anti-Pattern)",
            FindingCategory.CODE_QUALITY,
            FindingSeverity.LOW,
            "Silently suppressing all exceptions hides critical runtime failures and bugs.",
            "Log the exception explicitly or handle specific expected exception types.",
        ),
    ]

    def __init__(
        self,
        sandbox_root: Path | str | None = None,
        allowed_roots: list[Path | str] | None = None,
        max_file_size_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self.sandbox_root = Path(sandbox_root or "sandbox").resolve()
        self.allowed_roots = [Path(r).resolve() for r in allowed_roots] if allowed_roots is not None else None
        self.max_file_size_bytes = max_file_size_bytes

    def review_directory(
        self,
        directory_path: str,
        project_name: str = "Sandbox Project",
    ) -> ProjectReviewReport:
        """Analyze files within directory and return structured ProjectReviewReport with boundary and size guards."""
        raw_path = Path(directory_path)

        try:
            target_path = raw_path.resolve(strict=True)
        except (FileNotFoundError, RuntimeError):
            raise ProjectReviewError(f"Target project directory '{directory_path}' does not exist.")

        if not target_path.exists():
            raise ProjectReviewError(f"Target project directory '{directory_path}' does not exist.")

        if not target_path.is_dir():
            raise ProjectReviewError(f"Target path '{directory_path}' is not a directory.")

        # Workspace boundary enforcement: target path must reside within allowed roots if configured
        if self.allowed_roots:
            is_allowed = any(
                target_path == root or root in target_path.parents
                for root in self.allowed_roots
            )
            if not is_allowed:
                raise SandboxViolationError(
                    f"Target directory '{target_path}' is outside authorized workspace roots: {[str(r) for r in self.allowed_roots]}"
                )

        findings: list[ProjectFinding] = []
        files_analyzed = 0
        has_tests = False
        has_readme = False

        for root, _, filenames in os.walk(target_path):
            for fn in filenames:
                file_p = Path(root, fn)
                rel_path = str(file_p.relative_to(target_path))

                if "test" in rel_path.lower():
                    has_tests = True
                if "readme" in fn.lower():
                    has_readme = True

                # Check symlink boundary escape
                if file_p.is_symlink():
                    try:
                        resolved_file = file_p.resolve(strict=True)
                        if target_path not in resolved_file.parents and resolved_file != target_path:
                            findings.append(
                                ProjectFinding(
                                    title="Symlink Escapes Project Boundary",
                                    category=FindingCategory.SECURITY,
                                    severity=FindingSeverity.HIGH,
                                    file_path=rel_path,
                                    description=f"Symlink '{fn}' points to external location outside project root: {resolved_file}",
                                    remediation="Remove or re-point the symlink within the approved workspace root.",
                                )
                            )
                            continue
                    except Exception:
                        continue

                # Only inspect text source files (e.g. .py, .md, .json, .yaml, .txt, .sh, .js, .ts)
                if file_p.suffix.lower() in (".py", ".md", ".json", ".yaml", ".yml", ".txt", ".sh", ".js", ".ts"):
                    # Check per-file maximum size limit to prevent memory exhaustion
                    try:
                        file_stat = file_p.stat()
                        if file_stat.st_size > self.max_file_size_bytes:
                            findings.append(
                                ProjectFinding(
                                    title=f"File Skipped Due to Maximum Size Limit ({file_stat.st_size} bytes > {self.max_file_size_bytes} bytes)",
                                    category=FindingCategory.PERFORMANCE,
                                    severity=FindingSeverity.INFO,
                                    file_path=rel_path,
                                    description=f"File '{fn}' exceeds the maximum allowed inspection size of {self.max_file_size_bytes} bytes and was safely skipped.",
                                    remediation="Verify whether large data, database dumps, or logs should be excluded from static review.",
                                )
                            )
                            continue
                    except Exception:
                        continue

                    files_analyzed += 1
                    try:
                        content = file_p.read_text(encoding="utf-8", errors="ignore")
                        lines = content.splitlines()
                        for line_idx, line in enumerate(lines, start=1):
                            for pattern, title, cat, sev, desc, rem in self._SECURITY_PATTERNS:
                                if pattern.search(line):
                                    findings.append(
                                        ProjectFinding(
                                            title=title,
                                            category=cat,
                                            severity=sev,
                                            file_path=rel_path,
                                            line_number=line_idx,
                                            description=desc,
                                            remediation=rem,
                                        )
                                    )
                    except Exception:
                        continue

        # Check project-level architecture
        if files_analyzed > 3 and not has_tests:
            findings.append(
                ProjectFinding(
                    title="Missing Automated Test Suite",
                    category=FindingCategory.TESTING,
                    severity=FindingSeverity.MEDIUM,
                    file_path="tests/",
                    description="No automated test files were discovered in the project structure.",
                    remediation="Add a tests/ directory with unit and regression tests.",
                )
            )

        if not has_readme:
            findings.append(
                ProjectFinding(
                    title="Missing Project Documentation (README)",
                    category=FindingCategory.DOCUMENTATION,
                    severity=FindingSeverity.LOW,
                    file_path="README.md",
                    description="Project is missing a top-level README.md explaining architecture and setup.",
                    remediation="Create a comprehensive README.md with overview and instructions.",
                )
            )

        # Calculate health score
        total_deduction = sum(self.SEVERITY_DEDUCTIONS.get(f.severity, 1.0) for f in findings)
        health_score = max(0.0, min(100.0, 100.0 - total_deduction))

        # Generate proactive suggestions from findings
        suggestions: list[ProactiveSuggestion] = []
        if any(f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) for f in findings):
            suggestions.append(
                ProactiveSuggestion(
                    category=SuggestionCategory.SECURITY_HARDENING,
                    priority=SuggestionPriority.CRITICAL,
                    title="Remediate High/Critical Security Code Findings",
                    rationale="High-severity findings such as hardcoded secrets or dynamic eval require prompt remediation.",
                    recommended_steps=[
                        "Extract hardcoded credentials into environment configuration",
                        "Replace dynamic eval/exec with typed parsing abstractions",
                    ],
                    is_sensitive_action_required=False,
                )
            )

        if not has_tests and files_analyzed > 0:
            suggestions.append(
                ProactiveSuggestion(
                    category=SuggestionCategory.TESTING,
                    priority=SuggestionPriority.HIGH,
                    title="Implement Unit Test Coverage",
                    rationale="Automated test suites ensure ongoing reliability and prevent regressions.",
                    recommended_steps=[
                        "Create tests/ directory",
                        "Implement test cases for core components",
                    ],
                    is_sensitive_action_required=False,
                )
            )

        summary = (
            f"Autonomous review completed for {project_name}. Analyzed {files_analyzed} files. "
            f"Identified {len(findings)} findings. Overall health score: {health_score:.1f}/100.0."
        )

        return ProjectReviewReport(
            project_name=project_name,
            health_score=health_score,
            summary=summary,
            files_analyzed_count=files_analyzed,
            findings=findings,
            proactive_suggestions=suggestions,
            is_informational_only=True,
        )
