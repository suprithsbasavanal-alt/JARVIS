"""Central Service Registry managing external service adapters and lifecycle boundaries (Phase 9.1)."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

from core.context import SessionContext
from security.audit_logger import AuditLogger
from security.permissions import ApprovalToken
from services.base import BaseServiceAdapter
from services.models import (
    DuplicateServiceError,
    ServiceCapability,
    ServiceError,
    ServiceMetadata,
    ServiceNotFoundError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
)
from services.permissions import ServicePermissionBridge

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Central registry and dispatch coordinator for external service integrations."""

    def __init__(
        self,
        audit_logger: AuditLogger | None = None,
        permission_bridge: ServicePermissionBridge | None = None,
    ) -> None:
        self.audit_logger = audit_logger or AuditLogger()
        self.permission_bridge = permission_bridge or ServicePermissionBridge()
        self._adapters: dict[str, BaseServiceAdapter] = {}

    def register(self, adapter: BaseServiceAdapter) -> None:
        """Register a new service adapter. Rejects duplicates."""
        if not isinstance(adapter, BaseServiceAdapter):
            raise TypeError(f"Adapter must be an instance of BaseServiceAdapter, got {type(adapter)}")

        service_id = adapter.service_id
        if service_id in self._adapters:
            raise DuplicateServiceError(f"Service with ID '{service_id}' is already registered.")

        self._adapters[service_id] = adapter

        self.audit_logger.log(
            actor_id="service_registry",
            session_id="system",
            event_type="SERVICE_REGISTERED",
            action_type="REGISTRATION",
            risk_level="LOW",
            target_resource=f"service://{service_id}",
            parameters={
                "service_id": service_id,
                "name": adapter.metadata.name,
                "capabilities": [c.value for c in adapter.capabilities],
            },
            decision="SUCCESS",
        )

    def get(self, service_id: str) -> BaseServiceAdapter | None:
        """Retrieve a service adapter by ID, or None if not found."""
        return self._adapters.get(service_id)

    def get_or_raise(self, service_id: str) -> BaseServiceAdapter:
        """Retrieve a service adapter or raise ServiceNotFoundError."""
        adapter = self._adapters.get(service_id)
        if not adapter:
            raise ServiceNotFoundError(f"External service '{service_id}' is not registered.")
        return adapter

    def list_services(self) -> list[dict[str, Any]]:
        """Return safe, non-sensitive metadata for all registered services."""
        return [
            {
                **adapter.metadata.to_dict(),
                "status": adapter.status.value,
                "is_enabled": adapter.is_enabled,
            }
            for adapter in self._adapters.values()
        ]

    def get_capabilities(self, service_id: str) -> list[str]:
        """Return list of capability strings for a given service."""
        adapter = self.get_or_raise(service_id)
        return [c.value for c in adapter.capabilities]

    def enable(self, service_id: str) -> None:
        """Enable a registered service adapter."""
        adapter = self.get_or_raise(service_id)
        adapter.is_enabled = True

        self.audit_logger.log(
            actor_id="service_registry",
            session_id="system",
            event_type="SERVICE_ENABLED",
            action_type="ADMIN",
            risk_level="LOW",
            target_resource=f"service://{service_id}",
            parameters={"service_id": service_id},
            decision="SUCCESS",
        )

    def disable(self, service_id: str) -> None:
        """Disable a service adapter and disconnect active sessions."""
        adapter = self.get_or_raise(service_id)
        adapter.is_enabled = False

        self.audit_logger.log(
            actor_id="service_registry",
            session_id="system",
            event_type="SERVICE_DISABLED",
            action_type="ADMIN",
            risk_level="LOW",
            target_resource=f"service://{service_id}",
            parameters={"service_id": service_id},
            decision="SUCCESS",
        )

    async def revoke(self, service_id: str) -> None:
        """Revoke a service adapter, zeroize credentials, and mark REVOKED."""
        adapter = self.get_or_raise(service_id)
        await adapter.revoke()

        self.audit_logger.log(
            actor_id="service_registry",
            session_id="system",
            event_type="SERVICE_REVOKED",
            action_type="ADMIN",
            risk_level="MEDIUM",
            target_resource=f"service://{service_id}",
            parameters={"service_id": service_id},
            decision="SUCCESS",
        )

    async def execute(
        self,
        request: ServiceRequest,
        session: SessionContext,
        approval_token: ApprovalToken | None = None,
    ) -> ServiceResponse:
        """Execute a service operation through capability checks, HITL gates, and failure isolation."""
        adapter = self.get_or_raise(request.service_id)

        # 1. Evaluate permissions & HITL gates (may raise HumanConfirmationRequiredError)
        self.permission_bridge.evaluate_request(
            request=request,
            adapter=adapter,
            session=session,
            approval_token=approval_token,
        )

        # 2. Execute within failure isolation wrapper
        try:
            response = await asyncio.wait_for(adapter.execute(request), timeout=15.0)

            # 3. Log audit event
            self._log_audit_event(request, adapter, response.success, approval_token)
            return response

        except Exception as e:
            err_msg = f"Service '{request.service_id}' execution failed: {str(e)}"
            logger.error(err_msg, exc_info=True)

            self._log_audit_event(request, adapter, False, approval_token, error=err_msg)
            return ServiceResponse(
                service_id=request.service_id,
                operation=request.operation,
                success=False,
                data=None,
                error=err_msg,
                correlation_id=request.correlation_id,
            )

    async def health_check_all(self, timeout_seconds: float = 3.0) -> dict[str, str]:
        """Perform bounded health checks on all registered services without blocking indefinitely."""
        results: dict[str, str] = {}

        async def _check(sid: str, adp: BaseServiceAdapter) -> tuple[str, ServiceStatus]:
            try:
                status = await asyncio.wait_for(adp.health_check(), timeout=timeout_seconds)
                return sid, status
            except Exception:
                return sid, ServiceStatus.ERROR

        tasks = [_check(sid, adp) for sid, adp in self._adapters.items()]
        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for item in completed:
                if isinstance(item, tuple):
                    sid, status = item
                    results[sid] = status.value
                else:
                    pass

        return results

    def _log_audit_event(
        self,
        request: ServiceRequest,
        adapter: BaseServiceAdapter,
        success: bool,
        approval_token: ApprovalToken | None,
        error: str | None = None,
    ) -> None:
        """Write safe, non-repudiable audit log entry without credential leakage."""
        # Sanitize parameters (filter password, token, key, auth fields)
        safe_params = {
            k: ("[REDACTED]" if any(s in k.lower() for s in ["token", "secret", "password", "key", "auth"]) else v)
            for k, v in request.parameters.items()
        }

        self.audit_logger.log(
            actor_id="service_registry",
            session_id=request.session_id,
            event_type="SERVICE_OPERATION_EXECUTED" if success else "SERVICE_OPERATION_FAILED",
            action_type=f"{request.service_id}.{request.operation}",
            risk_level="HIGH" if request.capability in {ServiceCapability.SEND, ServiceCapability.DELETE} else "LOW",
            target_resource=f"service://{request.service_id}/{request.operation}",
            parameters={
                "capability": request.capability.value,
                "correlation_id": request.correlation_id,
                "safe_params": safe_params,
                "error": error,
            },
            decision="SUCCESS" if success else "FAILED",
            approval_token_id=str(approval_token.token_id) if approval_token else None,
        )
