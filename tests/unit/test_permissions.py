"""Unit tests for the PermissionEngine and ApprovalToken lifecycle."""

from config.schema import PermissionLevel
from core.context import SessionContext
from core.types import ActionCategory
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)


def test_permission_engine_locked_tier(permission_engine: PermissionEngine, session_context: SessionContext) -> None:
    """Verify LOCKED tier denies all tool execution."""
    session_context.permission_level = PermissionLevel.LOCKED
    decision = permission_engine.evaluate(
        session=session_context,
        action_name="web_search",
        required_level=PermissionLevel.NORMAL,
        action_category=ActionCategory.SAFE,
        target_resource="https://example.com",
        parameters={"q": "test"},
    )
    assert decision == PermissionDecision.DENIED_INSUFFICIENT_LEVEL


def test_permission_engine_sensitive_action_requires_approval(
    permission_engine: PermissionEngine, session_context: SessionContext
) -> None:
    """Verify SENSITIVE action without approval token triggers confirmation decision."""
    decision = permission_engine.evaluate(
        session=session_context,
        action_name="send_email",
        required_level=PermissionLevel.SENSITIVE,
        action_category=ActionCategory.SENSITIVE,
        target_resource="user@example.com",
        parameters={"to": "user@example.com", "body": "test"},
    )
    assert decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION


def test_permission_engine_sensitive_action_with_valid_token(
    permission_engine: PermissionEngine, session_context: SessionContext
) -> None:
    """Verify SENSITIVE action succeeds with valid approval token."""
    session_context.permission_level = PermissionLevel.SENSITIVE
    params = {"to": "user@example.com", "body": "test"}
    card = ApprovalCard.create(
        action_name="send_email",
        action_category=ActionCategory.SENSITIVE,
        target_resource="user@example.com",
        parameters=params,
        risk_summary="Send email test",
    )
    token = ApprovalToken(
        card_id=card.card_id,
        payload_hash=card.payload_hash,
        signature="mock-sig",
    )

    decision = permission_engine.evaluate(
        session=session_context,
        action_name="send_email",
        required_level=PermissionLevel.SENSITIVE,
        action_category=ActionCategory.SENSITIVE,
        target_resource="user@example.com",
        parameters=params,
        approval_token=token,
        card=card,
    )
    assert decision == PermissionDecision.AUTHORIZED


def test_permission_engine_emergency_lock(permission_engine: PermissionEngine, session_context: SessionContext) -> None:
    """Verify emergency lock rejects all operations immediately."""
    permission_engine.set_emergency_lock(True)
    decision = permission_engine.evaluate(
        session=session_context,
        action_name="safe_tool",
        required_level=PermissionLevel.NORMAL,
        action_category=ActionCategory.SAFE,
        target_resource="sandbox/fixtures/mock_files/notes.txt",
        parameters={},
    )
    assert decision == PermissionDecision.DENIED_EMERGENCY_LOCK
