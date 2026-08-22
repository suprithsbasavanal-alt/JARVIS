"""Core exception hierarchy for JARVIS.

Enforces clear error classification and fail-closed safety behaviors.
"""


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
    def __init__(self, action_name: str, approval_card_id: str, message: str | None = None) -> None:
        self.action_name = action_name
        self.approval_card_id = approval_card_id
        super().__init__(message or f"Action '{action_name}' requires human confirmation.")


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


class ToolExecutionError(JarvisError):
    """Raised when tool execution encounters runtime failure."""
    pass
