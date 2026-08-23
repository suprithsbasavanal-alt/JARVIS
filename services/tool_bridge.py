"""Bridge between Service Registry adapters and the AgentLoop ToolRegistry (Phase 9.1)."""

import json
from typing import Any

from config.schema import PermissionLevel
from core.context import SessionContext
from security.permissions import ApprovalToken
from services.models import ServiceCapability, ServiceRequest, ServiceResponse
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from tools.base import (
    BaseTool,
    RiskLevel,
    SideEffectLevel,
    ToolCapability,
    ToolDefinition,
    ToolResult,
)


class ServiceTool(BaseTool):
    """Dynamically generated BaseTool wrapping a specific service operation."""

    def __init__(
        self,
        service_id: str,
        operation: str,
        capability: ServiceCapability,
        description: str,
        service_registry: ServiceRegistry,
        parameters_schema: dict[str, Any] | None = None,
    ) -> None:
        tool_id = f"service_{service_id}_{operation}"
        name = f"service_{service_id}_{operation}"
        perm_level = ServicePermissionBridge.CAPABILITY_PERMISSION_MAP.get(
            capability, PermissionLevel.SENSITIVE
        )
        is_sensitive = (perm_level == PermissionLevel.SENSITIVE)

        definition = ToolDefinition(
            tool_id=tool_id,
            name=name,
            description=description,
            version="1.0.0",
            input_schema=parameters_schema or {
                "type": "object",
                "properties": {
                    "parameters": {"type": "object", "description": f"Parameters for {operation}"}
                },
            },
            capability=ToolCapability.COMMUNICATION if capability == ServiceCapability.SEND else ToolCapability.READ_ONLY,
            permission_tier=perm_level,
            risk_level=RiskLevel.HIGH if is_sensitive else RiskLevel.LOW,
            requires_confirmation=is_sensitive,
            side_effect_level=SideEffectLevel.WRITE if is_sensitive else SideEffectLevel.READ,
        )
        super().__init__(definition=definition)
        self.service_id = service_id
        self.operation = operation
        self.service_capability = capability
        self.service_registry = service_registry

    @property
    def name(self) -> str:
        return self.definition.name

    async def execute(
        self,
        parameters: dict[str, Any],
        context: SessionContext,
    ) -> ToolResult:
        """Execute the wrapped service operation via ServiceRegistry."""
        params = parameters.get("parameters", parameters) if "parameters" in parameters and isinstance(parameters["parameters"], dict) else parameters

        request = ServiceRequest(
            service_id=self.service_id,
            capability=self.service_capability,
            operation=self.operation,
            parameters=params,
            session_id=str(context.session_id) if hasattr(context, "session_id") else "default",
            correlation_id=str(context.correlation_id) if hasattr(context, "correlation_id") else "default",
        )

        response: ServiceResponse = await self.service_registry.execute(
            request=request,
            session=context,
        )

        return ToolResult(
            tool_id=self.definition.tool_id,
            tool_name=self.definition.name,
            is_success=response.success,
            output_data=response.to_dict(),
            error_message=response.error,
        )


def register_service_tools(service_registry: ServiceRegistry, tool_registry: Any) -> list[str]:
    """Helper to discover and register standard service tools into the JARVIS ToolRegistry."""
    registered_names: list[str] = []

    for svc in service_registry.list_services():
        sid = svc["service_id"]
        caps = svc["capabilities"]

        # If READ capability is present
        if ServiceCapability.READ.value in caps:
            t = ServiceTool(
                service_id=sid,
                operation="read_messages",
                capability=ServiceCapability.READ,
                description=f"Read inbox messages from external service '{sid}'.",
                service_registry=service_registry,
            )
            tool_registry.register_tool(t)
            registered_names.append(t.name)

        # If SEARCH capability is present
        if ServiceCapability.SEARCH.value in caps:
            t = ServiceTool(
                service_id=sid,
                operation="search_contacts",
                capability=ServiceCapability.SEARCH,
                description=f"Search contacts on external service '{sid}'.",
                service_registry=service_registry,
            )
            tool_registry.register_tool(t)
            registered_names.append(t.name)

        # If SEND capability is present
        if ServiceCapability.SEND.value in caps:
            t = ServiceTool(
                service_id=sid,
                operation="send_message",
                capability=ServiceCapability.SEND,
                description=f"Send an outbound message via external service '{sid}' (Requires HITL Confirmation).",
                service_registry=service_registry,
            )
            tool_registry.register_tool(t)
            registered_names.append(t.name)

    return registered_names
