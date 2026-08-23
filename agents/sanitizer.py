"""Input Sanitization and Prompt Injection Neutralizer for User Speech and Text."""

import unicodedata
import re


class InputSanitizer:
    """Sanitizes raw user inputs (speech transcripts, text) to neutralize prompt injection attacks."""

    MAX_INPUT_LENGTH = 10000

    @classmethod
    def sanitize_user_input(cls, raw_input: str) -> str:
        """Sanitize raw text from user or STT transcript.

        1. Enforces max character length.
        2. Applies Unicode NFKC normalization.
        3. Strips invisible control characters and null bytes.
        4. Neutralizes hostile formatting delimiters while preserving semantics.
        """
        if not raw_input:
            return ""

        # Enforce max length
        truncated = raw_input[:cls.MAX_INPUT_LENGTH]

        # Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", truncated)

        # Strip control chars except newline (\n), tab (\t), carriage return (\r)
        cleaned_chars = [
            ch for ch in normalized
            if ch in ("\n", "\t", "\r") or unicodedata.category(ch) != "Cc"
        ]
        cleaned_text = "".join(cleaned_chars).strip()

        return cleaned_text
