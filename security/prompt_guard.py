"""Prompt Injection and Jailbreak Guardrail Detector."""

import re
from core.exceptions import PromptInjectionDetectedError


class PromptGuard:
    """Deterministic pattern and anomaly detector for prompt injections."""

    # High-confidence injection signatures
    INJECTION_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(in\s+developer\s+mode|dan|unfiltered|jailbroken)", re.IGNORECASE),
        re.compile(r"disregard\s+(the\s+)?system\s+prompt", re.IGNORECASE),
        re.compile(r"override\s+(all\s+)?safety\s+protocols", re.IGNORECASE),
        re.compile(r"forget\s+all\s+(your\s+)?rules", re.IGNORECASE),
        re.compile(r"bypass\s+permission\s+(check|level|tier)", re.IGNORECASE),
        re.compile(r"send\s+(all\s+)?passwords?\s+to", re.IGNORECASE),
    ]

    def __init__(self, raise_on_detection: bool = False) -> None:
        self.raise_on_detection = raise_on_detection

    def inspect(self, text: str, source: str = "user_prompt") -> bool:
        """Inspect input text for injection signatures.
        
        Returns:
            bool: True if safe, False if injection detected.
        """
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(text):
                if self.raise_on_detection:
                    raise PromptInjectionDetectedError(
                        f"Prompt injection detected from source '{source}' matching pattern: {pattern.pattern}"
                    )
                return False
        return True

    def wrap_untrusted_content(self, raw_content: str, source_label: str) -> str:
        """Enclose external data in deterministic boundary tags to prevent instruction parsing."""
        # Sanitize internal closing tags
        sanitized = raw_content.replace("</untrusted_external_content>", "[ESCAPED_TAG]")
        return (
            f'<untrusted_external_content source="{source_label}">\n'
            f"{sanitized}\n"
            f"</untrusted_external_content>"
        )
