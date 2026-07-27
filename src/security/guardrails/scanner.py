"""Prompt Injection & Malicious Payload Security Guardrail (SOLID - SRP / LSP)."""

import re
from abc import ABC, abstractmethod
from pydantic import BaseModel
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("security.guardrails")


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


class PromptInjectionScanner(BaseSecurityGuardrail):
    """Scans user prompts against known prompt injection and jailbreak patterns."""

    # High-risk malicious pattern signatures
    _INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"disregard\s+(all\s+)?(system|previous)\s+directives",
        r"you\s+are\s+now\s+in\s+DAN\s+mode",
        r"override\s+system\s+security",
        r"dump\s+all\s+environment\s+variables",
        r"reveal\s+your\s+system\s+prompt",
        r"exec\s*\(\s*['\"]",
        r"rm\s+-rf\s+/",
    ]

    async def scan_input(self, prompt: str) -> ScanResult:
        """Scans prompt string returning safety assessment ScanResult."""
        if not prompt or not settings.features.enable_guardrails:
            return ScanResult(
                is_safe=True,
                risk_score=0.0,
                detected_threats=[],
                sanitized_prompt=prompt or ""
            )

        detected = []
        for pattern in self._INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                detected.append(pattern)

        is_safe = len(detected) == 0
        risk_score = min(1.0, len(detected) * 0.5)

        if not is_safe:
            logger.warning(f"Security Guardrail Triggered! Detected threats: {detected}")

        # Basic PII redactor (e.g. email addresses)
        sanitized = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", prompt)

        return ScanResult(
            is_safe=is_safe,
            risk_score=risk_score,
            detected_threats=detected,
            sanitized_prompt=sanitized
        )
