"""Unit tests for Authenticator, AuditLogger, and SecretVault."""

import pytest
from core.exceptions import AuthenticationError
from security.audit_logger import AuditLogger
from security.authenticator import Authenticator
from security.vault import MockSecretVault


def test_authenticator_enroll_and_validate(authenticator: Authenticator) -> None:
    """Verify device enrollment, session token generation, and validation."""
    device = authenticator.enroll_device("dev-01", "MacBook Pro", "fp-1234")
    assert device.device_id == "dev-01"
    assert not device.is_revoked

    token, secret = authenticator.authenticate_device("dev-01")
    assert authenticator.validate_session(token.token_id, secret)
    assert not authenticator.validate_session(token.token_id, "wrong-secret")


def test_authenticator_revocation(authenticator: Authenticator) -> None:
    """Verify revoking device invalidates all existing and future tokens."""
    authenticator.enroll_device("dev-02", "Android Phone", "fp-5678")
    token, secret = authenticator.authenticate_device("dev-02")
    assert authenticator.validate_session(token.token_id, secret)

    authenticator.revoke_device("dev-02")
    assert not authenticator.validate_session(token.token_id, secret)

    with pytest.raises(AuthenticationError):
        authenticator.authenticate_device("dev-02")


def test_audit_logger_hash_chain(audit_logger: AuditLogger) -> None:
    """Verify SHA-256 hash chaining in audit log and tampering detection."""
    audit_logger.log(
        actor_id="dev-01",
        action_type="CONVERSATION",
        permission_level="NORMAL",
        target_resource="memory",
        parameters={"q": "hello"},
        decision="AUTHORIZED",
    )
    audit_logger.log(
        actor_id="dev-01",
        action_type="TOOL_CALL",
        permission_level="SENSITIVE",
        target_resource="email",
        parameters={"to": "test@example.com"},
        decision="REQUIRES_CONFIRMATION",
    )

    assert len(audit_logger.get_entries()) == 2
    assert audit_logger.verify_integrity()

    # Simulate tampering with first entry
    entries = audit_logger.get_entries()
    entries[0].action_type = "TAMPERED_ACTION"
    assert not audit_logger.verify_integrity()


def test_mock_secret_vault() -> None:
    """Verify secret vault operations."""
    vault = MockSecretVault()
    vault.store_secret("API_KEY", "secret-value-123")
    assert vault.get_secret("API_KEY") == "secret-value-123"
    assert vault.get_secret("NONEXISTENT") is None

    assert vault.delete_secret("API_KEY")
    assert vault.get_secret("API_KEY") is None
    assert not vault.delete_secret("API_KEY")
