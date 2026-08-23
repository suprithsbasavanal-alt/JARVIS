"""Granular Permission & Capability Evaluation Engine for Phase 3."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4
from config.schema import PermissionLevel
from core.compat import BaseModel, Field
from core.context import SessionContext
from core.exceptions import (
    ApprovalTokenExpiredError,
    ApprovalTokenMismatchError,
    ApprovalTokenReplayError,
)
from core.types import ActionCategory


class PermissionDecision(str, Enum):
    """Result of a permission evaluation check."""
    AUTHORIZED = "AUTHORIZED"
    REQUIRES_HUMAN_CONFIRMATION = "REQUIRES_HUMAN_CONFIRMATION"
    DENIED_INSUFFICIENT_LEVEL = "DENIED_INSUFFICIENT_LEVEL"
    DENIED_RESOURCE_OUT_OF_BOUNDS = "DENIED_RESOURCE_OUT_OF_BOUNDS"
    DENIED_EMERGENCY_LOCK = "DENIED_EMERGENCY_LOCK"
    DENIED_DEFAULT = "DENIED_DEFAULT"


class ApprovalCard(BaseModel):
    """Structured human approval card for sensitive or destructive actions."""
    card_id: UUID = Field(default_factory=uuid4)
    action_name: str
    tool_id: str = ""
    tool_version: str = "1.0.0"
    risk_level: str = "HIGH"
    target_resource: str = "sandbox"
    parameter_payload: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str = ""
    risk_summary: str = ""
    session_id: str = ""
    correlation_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at_epoch: float = 0.0
    is_approved: bool = False
    is_cancelled: bool = False

    @classmethod
    def create(
        cls,
        action_name: str,
        action_category: ActionCategory | str,
        target_resource: str,
        parameters: dict[str, Any],
        risk_summary: str,
        tool_id: str = "",
        tool_version: str = "1.0.0",
        session_id: str = "",
        correlation_id: str = "",
        ttl_seconds: int = 300,
    ) -> "ApprovalCard":
        """Factory method to construct an approval card with payload hash and expiration."""
        payload_str = json.dumps(parameters, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc).timestamp() + ttl_seconds
        risk_str = action_category.value if isinstance(action_category, ActionCategory) else str(action_category)
        return cls(
            action_name=action_name,
            tool_id=tool_id or action_name,
            tool_version=tool_version,
            risk_level=risk_str,
            target_resource=target_resource,
            parameter_payload=parameters,
            payload_hash=payload_hash,
            risk_summary=risk_summary,
            session_id=session_id,
            correlation_id=correlation_id,
            expires_at_epoch=expires_at,
            is_approved=False,
            is_cancelled=False,
        )

    def cancel(self) -> None:
        """Explicitly cancel approval card, preventing token generation and execution."""
        self.is_cancelled = True


class ApprovalToken(BaseModel):
    """Single-use cryptographic confirmation token provided by the human owner."""
    token_id: UUID = Field(default_factory=uuid4)
    card_id: UUID
    tool_id: str = ""
    target_resource: str = ""
    session_id: str = ""
    payload_hash: str
    signature: str = "sig_sha256"
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_consumed: bool = False

    def validate_for(
        self,
        card: ApprovalCard,
        current_session_id: str = "",
        current_tool_id: str = "",
        current_target_resource: str = "",
    ) -> bool:
        """Strict validation of approval token integrity against approval card and execution context."""
        if self.is_consumed:
            raise ApprovalTokenReplayError("Approval token has already been consumed and cannot be replayed.")

        if card.is_cancelled:
            raise ApprovalTokenMismatchError("Approval card was cancelled by the user and cannot be authorized.")

        if self.card_id != card.card_id:
            raise ApprovalTokenMismatchError("Token card_id does not match approval card.")

        if self.payload_hash != card.payload_hash:
            raise ApprovalTokenMismatchError("Parameter hash in token does not match approval card.")

        if self.tool_id and card.tool_id and self.tool_id != card.tool_id:
            raise ApprovalTokenMismatchError(f"Token is bound to tool '{self.tool_id}', but card is '{card.tool_id}'.")

        if current_tool_id and self.tool_id and self.tool_id != current_tool_id:
            raise ApprovalTokenMismatchError(f"Token is bound to tool '{self.tool_id}', but executing '{current_tool_id}'.")

        if self.target_resource and card.target_resource and self.target_resource != card.target_resource:
            raise ApprovalTokenMismatchError(f"Token target '{self.target_resource}' does not match card target '{card.target_resource}'.")

        if current_target_resource and self.target_resource and self.target_resource != current_target_resource:
            raise ApprovalTokenMismatchError(f"Token target '{self.target_resource}' does not match executing target '{current_target_resource}'.")

        if self.session_id and current_session_id and self.session_id != current_session_id:
            raise ApprovalTokenMismatchError("Token is bound to a different session.")

        if datetime.now(timezone.utc).timestamp() > card.expires_at_epoch:
            raise ApprovalTokenExpiredError("Approval card and token have expired.")

        return True

    def is_valid_for(self, card: ApprovalCard) -> bool:
        """Backward compatible check returning boolean."""
        try:
            return self.validate_for(card)
        except Exception:
            return False

    def consume(self) -> None:
        """Mark token as consumed to prevent replay attacks."""
        self.is_consumed = True


class PermissionEngine:
    """Evaluator for capability and role-based access control with Default-Deny posture."""

    def __init__(self, emergency_locked: bool = False) -> None:
        self.emergency_locked = emergency_locked

    def set_emergency_lock(self, locked: bool) -> None:
        """Toggle emergency kill-switch lock."""
        self.emergency_locked = locked

    def evaluate(
        self,
        session: SessionContext,
        action_name: str,
        required_level: PermissionLevel,
        action_category: ActionCategory,
        target_resource: str,
        parameters: dict[str, Any],
        approval_token: ApprovalToken | None = None,
        card: ApprovalCard | None = None,
        tool_id: str = "",
    ) -> PermissionDecision:
        """Evaluate permission for a proposed tool action. Default Deny."""
        if self.emergency_locked:
            return PermissionDecision.DENIED_EMERGENCY_LOCK

        # 1. Level 0 (LOCKED) cannot run any tools under any circumstance
        if session.permission_level == PermissionLevel.LOCKED:
            return PermissionDecision.DENIED_INSUFFICIENT_LEVEL

        # 2. Check path traversal and whitelist enforcement for filesystem paths
        is_web_url = target_resource.startswith(("http://", "https://"))
        if not is_web_url and (target_resource.startswith("file://") or "/" in target_resource):
            clean_path = target_resource.removeprefix("file://")
            if ".." in clean_path:
                return PermissionDecision.DENIED_RESOURCE_OUT_OF_BOUNDS

            allowed = any(
                clean_path.startswith(whitelisted) or whitelisted in clean_path
                for whitelisted in session.active_whitelist_paths
            )
            if not allowed and not clean_path.startswith("sandbox/"):
                return PermissionDecision.DENIED_RESOURCE_OUT_OF_BOUNDS

        # 3. Actions classified as SENSITIVE, DESTRUCTIVE, or IRREVERSIBLE require HITL approval
        if action_category in (ActionCategory.SENSITIVE, ActionCategory.DESTRUCTIVE, ActionCategory.IRREVERSIBLE):
            if approval_token is None or card is None:
                return PermissionDecision.REQUIRES_HUMAN_CONFIRMATION
            try:
                approval_token.validate_for(
                    card,
                    current_session_id=str(session.session_id),
                    current_tool_id=tool_id or action_name,
                    current_target_resource=target_resource,
                )
            except Exception:
                return PermissionDecision.REQUIRES_HUMAN_CONFIRMATION

            return PermissionDecision.AUTHORIZED

        # 4. Safe and Reversible tools require session tier >= required_level
        tier_hierarchy = {
            PermissionLevel.LOCKED: 0,
            PermissionLevel.NORMAL: 1,
            PermissionLevel.SENSITIVE: 2,
        }
        user_tier_rank = tier_hierarchy.get(session.permission_level, 0)
        required_tier_rank = tier_hierarchy.get(required_level, 1)

        if user_tier_rank < required_tier_rank:
            return PermissionDecision.DENIED_INSUFFICIENT_LEVEL

        return PermissionDecision.AUTHORIZED
