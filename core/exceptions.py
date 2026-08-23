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


class ApprovalTokenError(SecurityError):
    """Base exception for approval token validation failures."""
    pass


class ApprovalTokenExpiredError(ApprovalTokenError):
    """Raised when an approval token has expired."""
    pass


class ApprovalTokenReplayError(ApprovalTokenError):
    """Raised when an approval token has already been consumed."""
    pass


class ApprovalTokenMismatchError(ApprovalTokenError):
    """Raised when an approval token does not match the tool, parameters, or session."""
    pass


class PromptInjectionDetectedError(SecurityError):
    """Raised when malicious prompt injection or jailbreak is detected."""
    pass


class SandboxViolationError(SecurityError):
    """Raised when an operation attempts to escape the sandbox."""
    pass


class ArbitraryShellExecutionBlockedError(SecurityError):
    """Raised when an unauthorized attempt to execute arbitrary shell commands is made."""
    pass


class NetworkAccessDisabledError(SecurityError):
    """Raised when an attempt to access external network is made in Phase 3."""
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


class DuplicateToolRegistrationError(ToolExecutionError):
    """Raised when registering a tool with an existing tool_id or name."""
    pass


class MalformedToolDefinitionError(ToolExecutionError):
    """Raised when a tool definition fails schema or contract validation."""
    pass


class MalformedToolRequestError(ToolExecutionError):
    """Raised when tool parameters fail validation against schema."""
    pass


class UnknownParameterError(MalformedToolRequestError):
    """Raised when unknown or undeclared parameters are passed to a tool."""
    pass


class ToolTimeoutError(ToolExecutionError):
    """Raised when tool execution exceeds its declared timeout limit."""
    pass


class OutputValidationError(SecurityError):
    """Raised when post-execution tool output fails schema or size validation."""
    pass


class VerificationFailureError(SecurityError):
    """Raised when post-execution tool verification fails."""
    pass


# ==============================================================================
# Phase 4.1: Secure Web Research Exceptions
# ==============================================================================

class WebResearchError(JarvisError):
    """Base exception for web research operations."""
    pass


class URLValidationError(SecurityError, WebResearchError):
    """Raised when a URL has an invalid scheme, contains userinfo/credentials, or is malformed."""
    pass


class SSRFBlockedError(SecurityError, WebResearchError):
    """Raised when an address resolves to a private, loopback, link-local, or cloud metadata IP."""
    pass


class RedirectBlockedError(SecurityError, WebResearchError):
    """Raised when a redirect hop violates SSRF/URL policy or exceeds hop limit."""
    pass


class PayloadSizeExceededError(SecurityError, WebResearchError):
    """Raised when a fetched web response exceeds the maximum allowed byte limit."""
    pass


class WebFetchTimeoutError(ToolTimeoutError, WebResearchError):
    """Raised when a web request connection or read timeout expires."""
    pass


# ==============================================================================
# Phase 4 Document Research Exceptions
# ==============================================================================

class DocumentError(JarvisError):
    """Base exception for document parsing and research operations."""
    pass


class DocumentParsingError(DocumentError):
    """Raised when document content fails syntactic or structural parsing."""
    pass


class DocumentSizeExceededError(SecurityError, DocumentError):
    """Raised when document file size or uncompressed stream exceeds maximum limit."""
    pass


class DocumentTimeoutError(ToolTimeoutError, DocumentError):
    """Raised when document parsing operation exceeds timeout limit."""
    pass


class DocumentFormatError(DocumentError):
    """Raised when unsupported or corrupted document format is encountered."""
    pass


# ==============================================================================
# Phase 5 Voice Pipeline Exceptions
# ==============================================================================

class VoiceError(JarvisError):
    """Base exception for voice pipeline and audio operations."""
    pass


class WakeWordDetectionError(VoiceError):
    """Raised when wake-word detection engine encounters runtime or parsing failure."""
    pass


class STTTranscriptionError(VoiceError):
    """Raised when speech-to-text transcription fails or receives malformed audio."""
    pass


class TTSSynthesisError(VoiceError):
    """Raised when text-to-speech audio synthesis fails."""
    pass


class VoiceBufferOverflowError(SecurityError, VoiceError):
    """Raised when in-memory audio ring buffer exceeds configured safety byte limit."""
    pass


class VoiceTimeoutError(ToolTimeoutError, VoiceError):
    """Raised when voice turn, wake-word listen, or transcription times out."""
    pass


class VoicePermissionDeniedError(PermissionDeniedError, VoiceError):
    """Raised when microphone or voice interaction is denied by active security policy."""
    pass


# ==============================================================================
# Phase 6 Proactive Intelligence & Reasoning Exceptions
# ==============================================================================

class ProactiveIntelligenceError(JarvisError):
    """Base exception for proactive recommendation and reasoning subsystems."""
    pass


class ProjectReviewError(ProactiveIntelligenceError):
    """Raised when autonomous project review fails or encounters malformed workspace."""
    pass


class PlanGenerationError(ProactiveIntelligenceError):
    """Raised when structured task or study plan generation fails."""
    pass


class ProactiveActionExecutionBlockedError(SecurityError, ProactiveIntelligenceError):
    """Raised when an unapproved attempt is made to automatically execute a proactive suggestion without user authorization."""
    pass




