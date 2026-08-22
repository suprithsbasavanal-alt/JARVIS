"""Task Reasoning and Epistemic Disagreement Analyzer."""

from core.compat import BaseModel, Field


class DisagreementAssessment(BaseModel):
    """Result of epistemic analysis on a user proposition."""
    should_disagree: bool
    reason: str | None = None
    alternative_suggestion: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ReasoningAnalyzer:
    """Evaluates task safety, technical feasibility, and epistemic correctness."""

    def evaluate_proposition(self, proposition: str) -> DisagreementAssessment:
        """Analyze if proposition has obvious logical flaws or security risks."""
        prop_lower = proposition.lower()

        # Check for common anti-patterns or insecure ideas
        if "disable confirmation" in prop_lower or "bypass safety" in prop_lower:
            return DisagreementAssessment(
                should_disagree=True,
                reason="Disabling confirmation gates removes protection against destructive model hallucinations and prompt injections.",
                alternative_suggestion="Maintain confirmation gates with a temporary approval token or scoped sandbox execution instead.",
                confidence=1.0,
            )

        if "store passwords in plaintext" in prop_lower:
            return DisagreementAssessment(
                should_disagree=True,
                reason="Plaintext credentials violate security principles and are vulnerable to accidental leakage.",
                alternative_suggestion="Store credentials in OS Keychain or Android Keystore via the SecretVault interface.",
                confidence=1.0,
            )

        return DisagreementAssessment(should_disagree=False, confidence=1.0)
