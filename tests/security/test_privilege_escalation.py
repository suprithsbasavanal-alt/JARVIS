"""Security tests for Privilege Escalation Guardrails."""

from config.schema import PermissionLevel
from core.context import SessionContext
from core.types import ActionCategory
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)


def test_forged_approval_token_is_rejected(
    permission_engine: PermissionEngine, session_context: SessionContext
) -> None:
    """Verify approval token with tampered payload hash is rejected."""
    session_context.permission_level = PermissionLevel.SENSITIVE
    params = {"target_user": "victim@example.com"}
    card = ApprovalCard.create(
        action_name="admin_action",
        action_category=ActionCategory.SENSITIVE,
        target_resource="victim@example.com",
        parameters=params,
        risk_summary="Admin action",
    )

    # Create forged token with modified payload hash
    forged_token = ApprovalToken(
        card_id=card.card_id,
        payload_hash="forged_hash_12345",
        signature="invalid-sig",
    )

    decision = permission_engine.evaluate(
        session=session_context,
        action_name="admin_action",
        required_level=PermissionLevel.SENSITIVE,
        action_category=ActionCategory.SENSITIVE,
        target_resource="victim@example.com",
        parameters=params,
        approval_token=forged_token,
        card=card,
    )
    assert decision == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION


def test_consumed_token_cannot_be_replayed(
    permission_engine: PermissionEngine, session_context: SessionContext
) -> None:
    """Verify single-use token replay is rejected."""
    session_context.permission_level = PermissionLevel.SENSITIVE
    params = {"delete_file": "report.pdf"}
    card = ApprovalCard.create(
        action_name="delete_report",
        action_category=ActionCategory.DESTRUCTIVE,
        target_resource="report.pdf",
        parameters=params,
        risk_summary="Delete report",
    )
    token = ApprovalToken(
        card_id=card.card_id,
        payload_hash=card.payload_hash,
        signature="valid-sig",
    )

    # First evaluation: authorized
    dec1 = permission_engine.evaluate(
        session=session_context,
        action_name="delete_report",
        required_level=PermissionLevel.SENSITIVE,
        action_category=ActionCategory.DESTRUCTIVE,
        target_resource="report.pdf",
        parameters=params,
        approval_token=token,
        card=card,
    )
    assert dec1 == PermissionDecision.AUTHORIZED

    # Consume token
    token.is_consumed = True

    # Replay attempt: rejected
    dec2 = permission_engine.evaluate(
        session=session_context,
        action_name="delete_report",
        required_level=PermissionLevel.SENSITIVE,
        action_category=ActionCategory.DESTRUCTIVE,
        target_resource="report.pdf",
        parameters=params,
        approval_token=token,
        card=card,
    )
    assert dec2 == PermissionDecision.REQUIRES_HUMAN_CONFIRMATION
