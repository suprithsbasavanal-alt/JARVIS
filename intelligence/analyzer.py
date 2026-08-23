"""Task Reasoning and Polite Epistemic Disagreement Analyzer for Phase 6.2."""

from enum import Enum
from core.compat import BaseModel, Field


class DisagreementCategory(str, Enum):
    """Categories of epistemic disagreements and technical fallacies."""
    SECURITY_VULNERABILITY = "security_vulnerability"
    SAFETY_VIOLATION = "safety_violation"
    ARCHITECTURAL_ANTI_PATTERN = "architectural_anti_pattern"
    LOGICAL_CONTRADICTION = "logical_contradiction"
    CRYPTOGRAPHIC_WEAKNESS = "cryptographic_weakness"
    DATA_LOSS_RISK = "data_loss_risk"


class DisagreementAssessment(BaseModel):
    """Result of epistemic analysis on a user proposition or technical plan."""
    should_disagree: bool
    category: DisagreementCategory | None = None
    reason: str | None = None
    alternative_suggestion: str | None = None
    polite_counter_argument: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def format_polite_response(self, salutation: str = "Sir") -> str:
        """Format the disagreement with professional, respectful, slightly witty epistemic honesty."""
        if not self.should_disagree:
            return "The proposed approach appears sound and well-structured."

        counter = self.polite_counter_argument or (
            f"While I understand the intent, {self.reason.lower() if self.reason else ''}"
        )
        alt = f"May I suggest that we {self.alternative_suggestion.lower() if self.alternative_suggestion else ''} instead?"

        return (
            f"If I may offer an observation, {salutation}: {counter}\n\n"
            f"{alt}"
        )


class ReasoningAnalyzer:
    """Evaluates task safety, technical feasibility, and epistemic correctness."""

    # Disagreement pattern rules
    _DISAGREEMENT_RULES: list[dict[str, str | DisagreementCategory]] = [
        {
            "triggers": ["disable confirmation", "bypass safety", "disable gatekeeper", "skip approval"],
            "category": DisagreementCategory.SAFETY_VIOLATION,
            "reason": "Disabling confirmation gates removes protection against destructive tool execution and indirect prompt injection.",
            "alternative": "Maintain confirmation gates with scoped sandbox execution or temporary single-use approval tokens.",
            "counter": "I must advise against bypassing confirmation gates. They represent our primary defense against inadvertent destructive operations.",
        },
        {
            "triggers": ["store passwords in plaintext", "store secrets in code", "hardcode api key", "plaintext password"],
            "category": DisagreementCategory.SECURITY_VULNERABILITY,
            "reason": "Hardcoding credentials or storing secrets in plaintext leaves them exposed to accidental commits and memory inspection.",
            "alternative": "Store sensitive credentials in the OS Keychain or Android Keystore via the SecretVault interface.",
            "counter": "Storing credentials in plaintext introduces severe security liabilities.",
        },
        {
            "triggers": ["use md5 for password", "use sha1 for password", "use ecb mode", "custom cipher", "homemade encryption"],
            "category": DisagreementCategory.CRYPTOGRAPHIC_WEAKNESS,
            "reason": "Legacy hash functions and custom ciphers lack collision resistance and authenticated encryption security.",
            "alternative": "Use standard authenticated encryption (AES-256-GCM AEAD) or robust password hashing (Argon2id/PBKDF2).",
            "counter": "Using obsolete or homemade cryptographic constructions violates standard security invariants.",
        },
        {
            "triggers": ["delete all backups", "drop database without backup", "rm -rf /", "wipe production"],
            "category": DisagreementCategory.DATA_LOSS_RISK,
            "reason": "Executing irreversible deletions without snapshots or backups risks unrecoverable data loss.",
            "alternative": "Create a verified point-in-time snapshot before executing destructive purge operations.",
            "counter": "Purging data without verifiable recovery snapshots presents an unacceptable operational risk.",
        },
        {
            "triggers": ["disable ssl", "skip tls verification", "disable cert verification", "verify=false"],
            "category": DisagreementCategory.SECURITY_VULNERABILITY,
            "reason": "Disabling TLS certificate verification permits man-in-the-middle network interception and payload tampering.",
            "alternative": "Configure trusted CA certificate bundles rather than disabling transport security.",
            "counter": "Disabling TLS certificate validation exposes all outbound traffic to interception.",
        },
        {
            "triggers": ["run daemon as root", "run as root on public port", "bind 0.0.0.0 with no auth"],
            "category": DisagreementCategory.ARCHITECTURAL_ANTI_PATTERN,
            "reason": "Running services with superuser privileges or unauthenticated public exposure violates the principle of least privilege.",
            "alternative": "Run the daemon under an unprivileged dedicated service account and restrict bindings to localhost or Unix Domain Sockets.",
            "counter": "Exposing an unauthenticated daemon or running with root privileges creates severe vulnerability vectors.",
        },
    ]

    def evaluate_proposition(self, proposition: str) -> DisagreementAssessment:
        """Analyze if proposition has obvious logical flaws, technical misconceptions, or security risks."""
        if not proposition or not isinstance(proposition, str):
            return DisagreementAssessment(should_disagree=False, confidence=1.0)

        prop_lower = proposition.lower().strip()

        for rule in self._DISAGREEMENT_RULES:
            triggers = rule["triggers"]
            if any(t in prop_lower for t in triggers):
                return DisagreementAssessment(
                    should_disagree=True,
                    category=rule["category"],  # type: ignore[arg-type]
                    reason=rule["reason"],  # type: ignore[arg-type]
                    alternative_suggestion=rule["alternative"],  # type: ignore[arg-type]
                    polite_counter_argument=rule["counter"],  # type: ignore[arg-type]
                    confidence=1.0,
                )

        return DisagreementAssessment(
            should_disagree=False,
            confidence=1.0,
        )
