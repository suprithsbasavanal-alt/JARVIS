"""Hermetic Gmail Service Connector for Email Management (Phase 9.2)."""

from typing import Any
from services.base import BaseCredentialProvider
from services.connectors.common import BaseHermeticConnector, ConnectorSimulationConfig
from services.models import (
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
)


class GmailConnector(BaseHermeticConnector):
    """Hermetic Gmail adapter supporting read_inbox, search_emails, create_draft, send_email, and delete_email."""

    def __init__(
        self,
        service_id: str = "gmail",
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="Google Gmail Connector",
            description="Hermetic adapter for reading, searching, drafting, sending, and deleting emails.",
            capabilities=frozenset({
                ServiceCapability.READ,
                ServiceCapability.SEARCH,
                ServiceCapability.CREATE,
                ServiceCapability.SEND,
                ServiceCapability.DELETE,
            }),
            version="1.0.0",
            auth_type="OAUTH2",
        )
        super().__init__(
            metadata=metadata,
            credential_provider=credential_provider,
            simulation_config=simulation_config,
        )

        # Synthetic in-memory state
        self._emails: list[dict[str, Any]] = [
            {
                "id": "email-001",
                "thread_id": "thread-101",
                "sender": "elon@x.com",
                "subject": "Starship Launch Telemetry",
                "body": "Telemetry stream synced. Ready for orbital insertion test.",
                "timestamp": "2026-08-23T08:00:00Z",
                "labels": ["INBOX", "IMPORTANT"],
            },
            {
                "id": "email-002",
                "thread_id": "thread-102",
                "sender": "sam@openai.com",
                "subject": "AGI Architecture Sync",
                "body": "Let's review the new reasoning models on Tuesday.",
                "timestamp": "2026-08-23T08:30:00Z",
                "labels": ["INBOX"],
            },
        ]
        self._drafts: list[dict[str, Any]] = []
        self._sent_emails: list[dict[str, Any]] = []

        # Default synthetic credentials
        self.credential_provider.set_credential(self.service_id, "oauth_token", "fake-gmail-bearer-token-12345")

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute Gmail operations after validating capability and simulations."""
        self.validate_capability(request.capability)
        await self._apply_simulations()

        op = request.operation.lower()

        # 1. READ
        if request.capability == ServiceCapability.READ:
            if op in {"read_inbox", "list_messages", "get_messages"}:
                limit = request.parameters.get("limit", 10)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"emails": self._emails[:limit], "count": len(self._emails[:limit])},
                    correlation_id=request.correlation_id,
                )
            if op in {"get_email", "get_message"}:
                email_id = request.parameters.get("email_id") or request.parameters.get("id")
                match = next((e for e in self._emails if e["id"] == email_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"Email '{email_id}' not found.",
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"email": match},
                    correlation_id=request.correlation_id,
                )

        # 2. SEARCH
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_emails", "search_messages"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    e for e in self._emails
                    if query in e["subject"].lower() or query in e["body"].lower() or query in e["sender"].lower()
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"emails": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )

        # 3. CREATE (Draft)
        if request.capability == ServiceCapability.CREATE:
            if op in {"create_draft", "save_draft"}:
                draft = {
                    "draft_id": f"draft-{len(self._drafts) + 1}",
                    "to": request.parameters.get("to", ""),
                    "subject": request.parameters.get("subject", "No Subject"),
                    "body": request.parameters.get("body", ""),
                }
                self._drafts.append(draft)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"draft": draft, "status": "DRAFT_SAVED"},
                    correlation_id=request.correlation_id,
                )

        # 4. SEND (Email)
        if request.capability == ServiceCapability.SEND:
            if op in {"send_email", "send_message"}:
                to = request.parameters.get("to") or request.parameters.get("recipient")
                subject = request.parameters.get("subject", "No Subject")
                body = request.parameters.get("body", "")

                if not to:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="Recipient ('to') is required to send email.",
                        correlation_id=request.correlation_id,
                    )

                sent = {
                    "id": f"sent-email-{len(self._sent_emails) + 1}",
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "status": "SENT",
                }
                self._sent_emails.append(sent)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"sent": sent, "status": "SENT"},
                    correlation_id=request.correlation_id,
                )

        # 5. DELETE
        if request.capability == ServiceCapability.DELETE:
            if op in {"delete_email", "delete_message", "trash_message"}:
                email_id = request.parameters.get("email_id") or request.parameters.get("id")
                initial_len = len(self._emails)
                self._emails = [e for e in self._emails if e["id"] != email_id]
                if len(self._emails) < initial_len:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=True,
                        data={"deleted_id": email_id, "status": "DELETED"},
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=False,
                    error=f"Email '{email_id}' not found to delete.",
                    correlation_id=request.correlation_id,
                )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )
