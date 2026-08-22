"""PII and Sensitive Data Sanitizer."""

import re
from typing import ClassVar


class Sanitizer:
    """Scans and redacts sensitive entities (API keys, credit cards, emails, tokens)."""

    PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "API_KEY": re.compile(r"\b(sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z-_]{35})\b"),
        "BEARER_TOKEN": re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.IGNORECASE),
        "CREDIT_CARD": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "PHONE_NUMBER": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    }

    def __init__(self) -> None:
        self._session_map: dict[str, str] = {}
        self._reverse_map: dict[str, str] = {}
        self._counter: int = 0

    def sanitize(self, text: str) -> str:
        """Replace detected PII entities with reversible token placeholders."""
        sanitized = text

        for p_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(sanitized)
            for match in matches:
                # If matched as tuple (e.g. from capture groups), extract full string
                match_val = match if isinstance(match, str) else match[0]
                if match_val not in self._session_map:
                    self._counter += 1
                    token = f"{{{{REDACTED_{p_type}_{self._counter}}}}}"
                    self._session_map[match_val] = token
                    self._reverse_map[token] = match_val
                sanitized = sanitized.replace(match_val, self._session_map[match_val])

        return sanitized

    def restore(self, text: str) -> str:
        """Restore redacted placeholders back to original values."""
        restored = text
        for token, original in self._reverse_map.items():
            restored = restored.replace(token, original)
        return restored
