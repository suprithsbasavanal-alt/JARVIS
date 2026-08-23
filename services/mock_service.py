"""Hermetic Mock Service Adapter for testing and foundation verification (Phase 9.1)."""

from typing import Any
from services.base import BaseCredentialProvider, BaseServiceAdapter, InMemoryCredentialProvider
from services.models import (
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
)


class MockMessagingServiceAdapter(BaseServiceAdapter):
    """Hermetic mock messaging adapter (e.g. mock email/chat) supporting READ, SEARCH, and SEND."""

    def __init__(
        self,
        service_id: str = "mock_messaging",
        credential_provider: BaseCredentialProvider | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="Mock Messaging Service",
            description="Hermetic in-memory mock service for messaging and contacts.",
            capabilities=frozenset({
                ServiceCapability.READ,
                ServiceCapability.SEARCH,
                ServiceCapability.SEND,
            }),
            version="1.0.0",
            auth_type="API_KEY",
        )
        super().__init__(metadata=metadata, credential_provider=credential_provider)
        self._status = ServiceStatus.CONNECTED

        # Synthetic in-memory state
        self._messages: list[dict[str, Any]] = [
            {"id": "msg-001", "sender": "tony@stark.com", "subject": "Mark LXXXV Diagnostics", "body": "Power grid stable."},
            {"id": "msg-002", "sender": "pepper@stark.com", "subject": "Board Meeting", "body": "Scheduled for 3:00 PM."},
        ]
        self._contacts: list[dict[str, Any]] = [
            {"id": "c-001", "name": "Tony Stark", "email": "tony@stark.com", "role": "CEO"},
            {"id": "c-002", "name": "Pepper Potts", "email": "pepper@stark.com", "role": "COO"},
            {"id": "c-003", "name": "James Rhodes", "email": "rhodey@usaf.mil", "role": "Colonel"},
        ]
        self._sent_messages: list[dict[str, Any]] = []

        # Seed initial credentials
        self.credential_provider.set_credential(self.service_id, "api_key", "mock-secret-key-12345")

    async def health_check(self) -> ServiceStatus:
        """Verify credential presence and connection status."""
        if not self.is_enabled:
            self._status = ServiceStatus.DISCONNECTED
            return self._status

        if not self.credential_provider.has_credentials(self.service_id):
            self._status = ServiceStatus.AUTH_REQUIRED
            return self._status

        self._status = ServiceStatus.CONNECTED
        return self._status

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute mock operations."""
        self.validate_capability(request.capability)

        if not self.credential_provider.has_credentials(self.service_id):
            raise ServiceAuthenticationError(f"Missing credentials for service '{self.service_id}'.")

        op = request.operation.lower()

        # READ operations
        if request.capability == ServiceCapability.READ:
            if op in {"read_messages", "read_inbox", "get_messages"}:
                limit = request.parameters.get("limit", 10)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"messages": self._messages[:limit], "count": len(self._messages[:limit])},
                    correlation_id=request.correlation_id,
                )
            return ServiceResponse(
                service_id=self.service_id,
                operation=request.operation,
                success=False,
                error=f"Unsupported READ operation '{request.operation}'.",
                correlation_id=request.correlation_id,
            )

        # SEARCH operations
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_contacts", "find_contacts"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    c for c in self._contacts
                    if query in c["name"].lower() or query in c["email"].lower()
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"contacts": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )
            return ServiceResponse(
                service_id=self.service_id,
                operation=request.operation,
                success=False,
                error=f"Unsupported SEARCH operation '{request.operation}'.",
                correlation_id=request.correlation_id,
            )

        # SEND operations
        if request.capability == ServiceCapability.SEND:
            if op in {"send_message", "send_email", "post_message"}:
                recipient = request.parameters.get("recipient") or request.parameters.get("to")
                body = request.parameters.get("body") or request.parameters.get("text") or ""
                subject = request.parameters.get("subject", "No Subject")

                if not recipient:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="Recipient is required for send operation.",
                        correlation_id=request.correlation_id,
                    )

                sent_record = {
                    "id": f"sent-{len(self._sent_messages) + 1}",
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                }
                self._sent_messages.append(sent_record)

                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"sent": sent_record, "status": "DELIVERED"},
                    correlation_id=request.correlation_id,
                )
            return ServiceResponse(
                service_id=self.service_id,
                operation=request.operation,
                success=False,
                error=f"Unsupported SEND operation '{request.operation}'.",
                correlation_id=request.correlation_id,
            )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )

    async def disconnect(self) -> None:
        """Disconnect adapter."""
        self._status = ServiceStatus.DISCONNECTED

    async def revoke(self) -> None:
        """Revoke credentials and disable adapter."""
        self.credential_provider.revoke_credentials(self.service_id)
        self._status = ServiceStatus.REVOKED
        self.is_enabled = False
