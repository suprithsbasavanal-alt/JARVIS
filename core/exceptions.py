"""Core exception hierarchy for JARVIS.

Enforces clear error classification and fail-closed safety behaviors.
"""

from typing import Any


class JarvisError(Exception):
    """Base exception for all JARVIS-specific errors."""
    pass


class SecurityError(JarvisError):
    """Base exception for security-related violations."""
    pass


class PermissionDeniedError(SecurityError):
    """Raised when an operation violates active permission policy."""
    pass


class HumanConfirmationRequiredError(SecurityError):
    """Raised when an action requires explicit human confirmation."""
    def __init__(self, action_name: str, approval_card: Any, message: str | None = None) -> None:
        self.action_name = action_name
        self.approval_card = approval_card
        card_id = getattr(approval_card, "card_id", "unknown")
        self.approval_card_id = str(card_id)
        super().__init__(message or f"Action '{action_name}' requires human confirmation (Card ID: {card_id}).")


class PromptInjectionDetectedError(SecurityError):
    """Raised when malicious prompt injection or jailbreak is detected."""
    pass


class SandboxViolationError(SecurityError):
    """Raised when an operation attempts to escape the sandbox."""
    pass


class AuthenticationError(SecurityError):
    """Raised when device or session authentication fails."""
    pass


class ModelRoutingError(JarvisError):
    """Raised when model dispatch or provider fallback fails."""
    pass


class ProviderUnavailableError(ModelRoutingError):
    """Raised when the requested model provider is offline or unreachable."""
    pass


class ToolExecutionError(JarvisError):
    """Raised when tool execution encounters runtime failure."""
    pass


class ToolNotFoundError(ToolExecutionError):
    """Raised when the requested tool is not found in the registry."""
    pass


class MalformedToolRequestError(ToolExecutionError):
    """Raised when tool parameters fail validation against schema."""
    pass


class VerificationFailureError(SecurityError):
    """Raised when post-execution tool verification fails."""
    pass
