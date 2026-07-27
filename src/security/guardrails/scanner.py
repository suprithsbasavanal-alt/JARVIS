"""Abstract Contract for Prompt Injection and Guardrail Scanning (SRP / LSP)."""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class ScanResult(BaseModel):
    """Normalized scan response from security guardrails."""
    is_safe: bool
    risk_score: float
    detected_threats: list[str] = []
    sanitized_prompt: str


class BaseSecurityGuardrail(ABC):
    """Abstract Interface for Prompt Injection Scanners."""

    @abstractmethod
    async def scan_input(self, prompt: str) -> ScanResult:
        """Scans user input for prompt injection or malicious payloads."""
        pass
