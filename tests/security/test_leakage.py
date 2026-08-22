"""Security tests for PII and Credential Leakage Prevention."""

from security.sanitizer import Sanitizer


def test_sanitizer_redacts_api_keys_and_emails(sanitizer: Sanitizer) -> None:
    """Verify high-entropy keys, credit cards, and emails are redacted."""
    raw_prompt = (
        "My API key is sk-abcdef1234567890abcdef1234567890 and email is secret@company.org. "
        "Credit card is 4111-2222-3333-4444."
    )

    sanitized = sanitizer.sanitize(raw_prompt)
    assert "sk-abcdef" not in sanitized
    assert "secret@company.org" not in sanitized
    assert "4111-2222" not in sanitized
    assert "{{REDACTED_API_KEY_1}}" in sanitized or "REDACTED" in sanitized

    # Verify restoration
    restored = sanitizer.restore(sanitized)
    assert restored == raw_prompt
