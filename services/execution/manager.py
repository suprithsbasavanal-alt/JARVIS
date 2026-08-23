"""Central Production Service Execution Manager with HITL, Idempotency, and Transport Gate (Phase 9.4)."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any

from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from security.audit_logger import AuditLogger
from security.permissions import ApprovalToken
from services.base import BaseServiceAdapter
from services.credentials.provider import SecureCredentialManager
from services.execution.idempotency import IdempotencyManager
from services.models import (
    ServiceCapability,
    ServiceDisabledError,
    ServiceError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from services.transport.base import BaseHttpTransport
from services.transport.models import TransportError, TransportUnavailableError

logger = logging.getLogger(__name__)


class EmergencyStopActiveError(ServiceError):
    """Raised when external service execution is blocked due to active emergency stop."""
    pass


class ServiceExecutionManager:
    """Central execution gateway governing external service operations with strict security invariants."""

    MUTATION_CAPABILITIES = frozenset({
        ServiceCapability.SEND,
        ServiceCapability.CREATE,
        ServiceCapability.UPDATE,
        ServiceCapability.DELETE,
        ServiceCapability.EXECUTE,
    })

    def __init__(
        self,
        service_registry: ServiceRegistry,
        permission_bridge: ServicePermissionBridge,
        credential_manager: SecureCredentialManager,
        transport: BaseHttpTransport,
        audit_logger: AuditLogger,
        idempotency_manager: IdempotencyManager | None = None,
        is_emergency_stop_active: bool = False,
    ) -> None:
        self.service_registry = service_registry
        self.permission_bridge = permission_bridge
        self.credential_manager = credential_manager
        self.transport = transport
        self.audit_logger = audit_logger
        self.idempotency_manager = idempotency_manager or IdempotencyManager()
        self.is_emergency_stop_active = is_emergency_stop_active

    def trigger_emergency_stop(self) -> None:
        """Immediately block all subsequent external service execution."""
        self.is_emergency_stop_active = True

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop flag."""
        self.is_emergency_stop_active = False

    async def execute(
        self,
        request: ServiceRequest,
        session: SessionContext,
        approval_token: ApprovalToken | None = None,
        idempotency_key: str | None = None,
    ) -> ServiceResponse:
        """Execute a service operation through the complete security and transport gatekeeper."""
        start_time = time.monotonic()

        # 1. Emergency stop check
        if self.is_emergency_stop_active:
            err_msg = "External service execution halted: Emergency Stop is active."
            self._log_audit(request, None, False, approval_token, error=err_msg, latency=0.0)
            raise EmergencyStopActiveError(err_msg)

        # 2. Lookup adapter and verify enabled/revoked state
        adapter = self.service_registry.get_or_raise(request.service_id)
        if not adapter.is_enabled or adapter.status == ServiceStatus.REVOKED:
            err_msg = f"Service '{request.service_id}' is disabled or revoked."
            self._log_audit(request, adapter, False, approval_token, error=err_msg, latency=0.0)
            raise ServiceDisabledError(err_msg)

        # 3. Verify declared capability
        adapter.validate_capability(request.capability)

        # 4. Duplicate / Idempotency check for mutations
        is_mutation = request.capability in self.MUTATION_CAPABILITIES
        fingerprint = ""
        if is_mutation:
            is_dup, prev_record, fingerprint = self.idempotency_manager.check_or_start(
                service_id=request.service_id,
                operation=request.operation,
                parameters=request.parameters,
                idempotency_key=idempotency_key,
            )
            if is_dup and prev_record and prev_record.response:
                logger.info("Returning cached idempotent response for %s.%s", request.service_id, request.operation)
                return prev_record.response

        # 5. Permission & HITL Evaluation (may raise HumanConfirmationRequiredError)
        try:
            self.permission_bridge.evaluate_request(
                request=request,
                adapter=adapter,
                session=session,
                approval_token=approval_token,
            )
        except Exception:
            if is_mutation and fingerprint:
                self.idempotency_manager.record_failed(fingerprint)
            raise

        # 6. Execute adapter with bounded timeout
        try:
            # If adapter supports transport injection, assign it
            if hasattr(adapter, "transport"):
                adapter.transport = self.transport

            response: ServiceResponse = await asyncio.wait_for(
                adapter.execute(request),
                timeout=15.0,
            )

            latency = time.monotonic() - start_time

            # 7. Record idempotency completion
            if is_mutation and fingerprint:
                self.idempotency_manager.record_completed(fingerprint, response)

            # 8. Non-repudiable audit logging
            self._log_audit(request, adapter, response.success, approval_token, latency=latency, error=response.error)
            return response

        except Exception as e:
            latency = time.monotonic() - start_time
            if is_mutation and fingerprint:
                self.idempotency_manager.record_failed(fingerprint)

            err_msg = f"Service '{request.service_id}' execution failed: {str(e)}"
            logger.error(err_msg, exc_info=True)
            self._log_audit(request, adapter, False, approval_token, latency=latency, error=err_msg)

            return ServiceResponse(
                service_id=request.service_id,
                operation=request.operation,
                success=False,
                data=None,
                error=err_msg,
                correlation_id=request.correlation_id,
            )

    def _log_audit(
        self,
        request: ServiceRequest,
        adapter: BaseServiceAdapter | None,
        success: bool,
        approval_token: ApprovalToken | None,
        latency: float = 0.0,
        error: str | None = None,
    ) -> None:
        """Write sanitized, non-repudiable chained audit log entry."""
        sanitized_params = {}
        for k, v in request.parameters.items():
            if any(secret_kw in k.lower() for secret_kw in {"token", "secret", "password", "key", "auth", "credential"}):
                sanitized_params[k] = "[REDACTED]"
            else:
                sanitized_params[k] = v

        action_type = "COMMUNICATION" if request.capability == ServiceCapability.SEND else "SERVICE_OPERATION"
        risk_level = "HIGH" if request.capability in self.MUTATION_CAPABILITIES else "LOW"

        self.audit_logger.log(
            actor_id=str(request.session_id),
            session_id=str(request.session_id),
            event_type="SERVICE_EXTERNAL_OPERATION",
            action_type=action_type,
            risk_level=risk_level,
            target_resource=f"service://{request.service_id}/{request.operation}",
            parameters={
                "service_id": request.service_id,
                "operation": request.operation,
                "capability": request.capability.value,
                "parameters": sanitized_params,
                "latency_seconds": round(latency, 4),
                "approval_token_used": bool(approval_token),
                "error": error,
            },
            decision="SUCCESS" if success else "FAILURE",
        )
