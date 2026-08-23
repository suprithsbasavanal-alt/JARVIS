"""Permission Engine integration and Capability Access Control for External Services (Phase 9.1)."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from core.types import ActionCategory
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)
from services.base import BaseServiceAdapter
from services.models import (
    ServiceCapability,
    ServiceDisabledError,
    ServiceRequest,
    ServiceStatus,
    UndeclaredCapabilityError,
)


class ServicePermissionBridge:
    """Bridges External Service requests with the central PermissionEngine and HITL Gatekeeper."""

    # Explicit mapping of Service Capabilities to JARVIS Permission Levels
    CAPABILITY_PERMISSION_MAP: dict[ServiceCapability, PermissionLevel] = {
        ServiceCapability.READ: PermissionLevel.NORMAL,
        ServiceCapability.SEARCH: PermissionLevel.NORMAL,
        ServiceCapability.CREATE: PermissionLevel.SENSITIVE,
        ServiceCapability.UPDATE: PermissionLevel.SENSITIVE,
        ServiceCapability.DELETE: PermissionLevel.SENSITIVE,
        ServiceCapability.SEND: PermissionLevel.SENSITIVE,
        ServiceCapability.EXECUTE: PermissionLevel.SENSITIVE,
    }

    def __init__(self, permission_engine: PermissionEngine | None = None) -> None:
        self.permission_engine = permission_engine or PermissionEngine()

    def get_permission_level_for_capability(self, capability: ServiceCapability) -> PermissionLevel:
        """Return the required permission tier for a given capability."""
        return self.CAPABILITY_PERMISSION_MAP.get(capability, PermissionLevel.SENSITIVE)

    def evaluate_request(
        self,
        request: ServiceRequest,
        adapter: BaseServiceAdapter,
        session: SessionContext,
        approval_token: ApprovalToken | None = None,
    ) -> PermissionDecision:
        """Evaluate a service request against capability constraints and HITL permission gates."""
        # 1. Verify service adapter is enabled
        if not adapter.is_enabled or adapter.status == ServiceStatus.REVOKED:
            raise ServiceDisabledError(
                f"Service '{adapter.service_id}' is disabled or revoked."
            )

        # 2. Verify capability is declared by adapter
        adapter.validate_capability(request.capability)

        # 3. Determine permission tier
        perm_level = self.get_permission_level_for_capability(request.capability)
        tool_id = f"service_{adapter.service_id}_{request.operation}"
        target_resource = f"{adapter.service_id}://{request.operation}"

        # 4. If SENSITIVE, enforce HITL ApprovalCard + single-use ApprovalToken
        if perm_level == PermissionLevel.SENSITIVE:
            if not approval_token:
                card = ApprovalCard.create(
                    action_name=f"{adapter.metadata.name}: {request.operation}",
                    action_category=ActionCategory.SENSITIVE,
                    target_resource=target_resource,
                    parameters=request.parameters,
                    risk_summary=f"External service operation '{request.operation}' with capability '{request.capability.value}'.",
                    tool_id=tool_id,
                    session_id=str(session.session_id),
                    correlation_id=str(session.correlation_id),
                )
                raise HumanConfirmationRequiredError(
                    f"External service operation '{request.operation}' on '{adapter.service_id}' requires explicit human authorization.",
                    approval_card=card,
                )

            # Reconstruct matching card for token validation
            card = ApprovalCard.create(
                action_name=f"{adapter.metadata.name}: {request.operation}",
                action_category=ActionCategory.SENSITIVE,
                target_resource=target_resource,
                parameters=request.parameters,
                risk_summary=f"External service operation '{request.operation}' with capability '{request.capability.value}'.",
                tool_id=tool_id,
                session_id=str(session.session_id),
                correlation_id=str(session.correlation_id),
            )
            card.card_id = approval_token.card_id

            try:
                approval_token.validate_for(
                    card=card,
                    current_session_id=str(session.session_id),
                    current_tool_id=tool_id,
                    current_target_resource=target_resource,
                )
                approval_token.consume()
            except Exception as ex:
                raise PermissionDeniedError(f"Permission denied: {str(ex)}") from ex

            return PermissionDecision.AUTHORIZED

        # 5. For NORMAL permissions, evaluate via PermissionEngine
        return self.permission_engine.evaluate(
            session=session,
            action_name=f"{adapter.service_id}.{request.operation}",
            required_level=perm_level,
            action_category=ActionCategory.SAFE,
            target_resource=target_resource,
            parameters=request.parameters,
            approval_token=approval_token,
            tool_id=tool_id,
        )
