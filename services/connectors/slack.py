"""Hermetic Slack Service Connector for Team Chat & Channel Communications (Phase 9.2)."""

from typing import Any
from services.base import BaseCredentialProvider
from services.connectors.common import BaseHermeticConnector, ConnectorSimulationConfig
from services.models import (
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
)


from services.transport.base import BaseHttpTransport


class SlackConnector(BaseHermeticConnector):
    """Hermetic & Production-ready Slack adapter supporting read_channel_history, search_messages, post_message, and delete_message."""

    def __init__(
        self,
        service_id: str = "slack",
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
        transport: BaseHttpTransport | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="Slack Team Messaging Connector",
            description="Hermetic adapter for workspace channels, direct messages, and chat history.",
            capabilities=frozenset({
                ServiceCapability.READ,
                ServiceCapability.SEARCH,
                ServiceCapability.SEND,
                ServiceCapability.DELETE,
            }),
            version="1.0.0",
            auth_type="BOT_TOKEN",
        )
        super().__init__(
            metadata=metadata,
            credential_provider=credential_provider,
            simulation_config=simulation_config,
            transport=transport,
        )

        # Synthetic in-memory channels and messages
        self._messages: list[dict[str, Any]] = [
            {
                "id": "msg-slack-001",
                "channel": "#engineering",
                "user": "tony",
                "text": "Mark 85 thruster calibration passing 99.4% threshold.",
                "timestamp": "2026-08-23T07:15:00Z",
            },
            {
                "id": "msg-slack-002",
                "channel": "#general",
                "user": "rhodey",
                "text": "Standby for DARPA flight inspection at 14:00.",
                "timestamp": "2026-08-23T08:45:00Z",
            },
        ]

        # Default synthetic credentials
        self.credential_provider.set_credential(self.service_id, "bot_token", "xoxb-fake-slack-bot-token-12345")

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute Slack operations."""
        self.validate_capability(request.capability)
        await self._apply_simulations()

        op = request.operation.lower()

        # 1. READ
        if request.capability == ServiceCapability.READ:
            if op in {"read_channel_history", "list_messages", "get_messages"}:
                channel = request.parameters.get("channel")
                limit = request.parameters.get("limit", 10)
                filtered = [m for m in self._messages if not channel or m["channel"] == channel]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"messages": filtered[:limit], "count": len(filtered[:limit])},
                    correlation_id=request.correlation_id,
                )
            if op in {"get_message", "message_details"}:
                msg_id = request.parameters.get("message_id") or request.parameters.get("id")
                match = next((m for m in self._messages if m["id"] == msg_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"Slack message '{msg_id}' not found.",
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"message": match},
                    correlation_id=request.correlation_id,
                )

        # 2. SEARCH
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_messages", "find_messages"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    m for m in self._messages
                    if query in m["text"].lower() or query in m["user"].lower() or query in m["channel"].lower()
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"messages": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )

        # 3. SEND
        if request.capability == ServiceCapability.SEND:
            if op in {"post_message", "send_message", "chat_post"}:
                channel = request.parameters.get("channel", "#general")
                text = request.parameters.get("text") or request.parameters.get("message")
                if not text:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="Message text is required to post to Slack.",
                        correlation_id=request.correlation_id,
                    )

                new_msg = {
                    "id": f"msg-slack-{len(self._messages) + 1:03d}",
                    "channel": channel,
                    "user": "jarvis-bot",
                    "text": text,
                    "timestamp": "2026-08-23T09:15:00Z",
                }
                self._messages.append(new_msg)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"message": new_msg, "status": "POSTED"},
                    correlation_id=request.correlation_id,
                )

        # 4. DELETE
        if request.capability == ServiceCapability.DELETE:
            if op in {"delete_message", "chat_delete"}:
                msg_id = request.parameters.get("message_id") or request.parameters.get("id")
                initial_len = len(self._messages)
                self._messages = [m for m in self._messages if m["id"] != msg_id]
                if len(self._messages) < initial_len:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=True,
                        data={"deleted_id": msg_id, "status": "DELETED"},
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=False,
                    error=f"Slack message '{msg_id}' not found to delete.",
                    correlation_id=request.correlation_id,
                )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )
