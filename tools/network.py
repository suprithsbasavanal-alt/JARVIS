"""Network Tool Contract and Disabled Network Guards for Phase 3."""

from typing import Any
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import NetworkAccessDisabledError
from tools.base import BaseTool, RiskLevel, SideEffectLevel, ToolCapability, ToolDefinition, ToolResult


class NetworkTool(BaseTool):
    """Abstract interface for future network-enabled tools. Strictly disabled in Phase 3."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            ToolDefinition(
                tool_id=tool_id,
                name=name,
                description=description,
                capability=ToolCapability.NETWORK,
                permission_tier=PermissionLevel.SENSITIVE,
                risk_level=RiskLevel.HIGH,
                allowed_environment="DISABLED",
                requires_confirmation=True,
                side_effect_level=SideEffectLevel.IRREVERSIBLE,
                input_schema=input_schema or {},
            )
        )

    async def execute(self, parameters: dict[str, Any], context: SessionContext) -> ToolResult:
        """Always fail closed with NetworkAccessDisabledError in Phase 3."""
        raise NetworkAccessDisabledError(
            f"Network tool '{self.definition.name}' is disabled in Phase 3. "
            "Real external network communication is strictly forbidden."
        )
