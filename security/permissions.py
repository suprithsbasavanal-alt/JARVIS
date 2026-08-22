"""Granular Permission & Capability Evaluation Engine."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from config.schema import PermissionLevel
from core.context import SessionContext
from core.types import ActionCategory


class PermissionDecision(str, Enum):
    """Result of a permission evaluation check."""
    AUTHORIZED = "AUTHORIZED"
    REQUIRES_HUMAN_CONFIRMATION = "REQUIRES_HUMAN_CONFIRMATION"
    DENIED_INSUFFICIENT_LEVEL = "DENIED_INSUFFICIENT_LEVEL"
    DENIED_RESOURCE_OUT_OF_BOUNDS = "DENIED_RESOURCE_OUT_OF_BOUNDS"
    DENIED_EMERGENCY_LOCK = "DENIED_EMERGENCY_LOCK"


class ApprovalCard(BaseModel):
    """Structured human approval card for sensitive or destructive actions."""
    card_id: UUID = Field(default_factory=uuid4)
    action_name: str
    action_category: ActionCategory
    target_resource: str
    parameter_payload: dict[str, Any]
    payload_hash: str
    risk_summary: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at_epoch: float

    @classmethod
    def create(
        cls,
        action_name: str,
        action_category: ActionCategory,
        target_resource: str,
        parameters: dict[str, Any],
        risk_summary: str,
        ttl_seconds: int = 60
    ) -> "ApprovalCard":
        """Factory method to construct an approval card with payload hash and expiration."""
        payload_str = json.dumps(parameters, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc).timestamp() + ttl_seconds
        return cls(
            action_name=action_name,
            action_category=action_category,
            target_resource=target_resource,
            parameter_payload=parameters,
            payload_hash=payload_hash,
            risk_summary=risk_summary,
            expires_at_epoch=expires_at,
        )


class ApprovalToken(BaseModel):
    """Single-use cryptographic confirmation token provided by the human owner."""
    token_id: UUID = Field(default_factory=uuid4)
    card_id: UUID
    payload_hash: str
    signature: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_consumed: bool = False

    def is_valid_for(self, card: ApprovalCard) -> bool:
        """Verify token integrity against approval card."""
        if self.is_consumed:
            return False
        if self.card_id != card.card_id:
            return False
        if self.payload_hash != card.payload_hash:
            return False
        if datetime.now(timezone.utc).timestamp() > card.expires_at_epoch:
            return False
        return True


class PermissionEngine:
    """Evaluator for role and capability-based access control."""

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
    ) -> PermissionDecision:
        """Evaluate permission for a proposed tool action."""
        if self.emergency_locked:
            return PermissionDecision.DENIED_EMERGENCY_LOCK

        # Level 0 (LOCKED) cannot run any tools
        if session.permission_level == PermissionLevel.LOCKED:
            return PermissionDecision.DENIED_INSUFFICIENT_LEVEL

        # Normal tier trying to run sensitive tools
        tier_hierarchy = {
            PermissionLevel.LOCKED: 0,
            PermissionLevel.NORMAL: 1,
            PermissionLevel.SENSITIVE: 2,
        }
        if tier_hierarchy[session.permission_level] < tier_hierarchy[required_level]:
            return PermissionDecision.DENIED_INSUFFICIENT_LEVEL

        # Actions classified as SENSITIVE, DESTRUCTIVE, or IRREVERSIBLE require HITL approval
        if action_category in (ActionCategory.SENSITIVE, ActionCategory.DESTRUCTIVE, ActionCategory.IRREVERSIBLE):
            if approval_token is None or card is None or not approval_token.is_valid_for(card):
                return PermissionDecision.REQUIRES_HUMAN_CONFIRMATION

        # Path traversal and whitelist enforcement
        if target_resource.startswith("file://") or "/" in target_resource:
            clean_path = target_resource.removeprefix("file://")
            allowed = any(clean_path.startswith(whitelisted) for whitelisted in session.active_whitelist_paths)
            if not allowed:
                return PermissionDecision.DENIED_RESOURCE_OUT_OF_BOUNDS

        return PermissionDecision.AUTHORIZED
