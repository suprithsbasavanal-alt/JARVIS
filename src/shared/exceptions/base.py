"""Jarvis Domain Exception Taxonomy."""


class JarvisException(Exception):
    """Base exception class for all Jarvis domain errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigurationError(JarvisException):
    """Raised when configuration is missing or invalid."""
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")


class LLMProviderError(JarvisException):
    """Raised when an AI model provider call fails."""
    def __init__(self, message: str):
        super().__init__(message, code="LLM_PROVIDER_ERROR")


class ToolExecutionError(JarvisException):
    """Raised when a tool execution fails or violates sandbox policies."""
    def __init__(self, message: str):
        super().__init__(message, code="TOOL_EXECUTION_ERROR")


class SecurityViolationError(JarvisException):
    """Raised when a security guardrail or auth check fails."""
    def __init__(self, message: str):
        super().__init__(message, code="SECURITY_VIOLATION")
