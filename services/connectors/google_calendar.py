"""Hermetic Google Calendar Service Connector for Event Scheduling (Phase 9.2)."""

from typing import Any
from services.base import BaseCredentialProvider
from services.connectors.common import BaseHermeticConnector, ConnectorSimulationConfig
from services.models import (
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
)


class GoogleCalendarConnector(BaseHermeticConnector):
    """Hermetic Google Calendar adapter supporting list_events, search_events, create_event, update_event, and delete_event."""

    def __init__(
        self,
        service_id: str = "google_calendar",
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="Google Calendar Connector",
            description="Hermetic adapter for calendar events, meetings, and schedules.",
            capabilities=frozenset({
                ServiceCapability.READ,
                ServiceCapability.SEARCH,
                ServiceCapability.CREATE,
                ServiceCapability.UPDATE,
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

        # Synthetic in-memory calendar events
        self._events: list[dict[str, Any]] = [
            {
                "id": "event-001",
                "summary": "Stark Industries Board Review",
                "start_time": "2026-08-25T14:00:00Z",
                "end_time": "2026-08-25T15:30:00Z",
                "attendees": ["tony@stark.com", "pepper@stark.com"],
                "location": "HQ Conference Room Alpha",
                "status": "CONFIRMED",
            },
            {
                "id": "event-002",
                "summary": "Avenger Tactical Briefing",
                "start_time": "2026-08-26T10:00:00Z",
                "end_time": "2026-08-26T11:00:00Z",
                "attendees": ["rhodey@usaf.mil", "tony@stark.com"],
                "location": "Compound Hangar",
                "status": "CONFIRMED",
            },
        ]

        # Default synthetic credentials
        self.credential_provider.set_credential(self.service_id, "oauth_token", "fake-gcal-bearer-token-12345")

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute Calendar operations."""
        self.validate_capability(request.capability)
        await self._apply_simulations()

        op = request.operation.lower()

        # 1. READ
        if request.capability == ServiceCapability.READ:
            if op in {"list_events", "get_events", "get_calendar"}:
                limit = request.parameters.get("limit", 10)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"events": self._events[:limit], "count": len(self._events[:limit])},
                    correlation_id=request.correlation_id,
                )
            if op in {"get_event", "event_details"}:
                event_id = request.parameters.get("event_id") or request.parameters.get("id")
                match = next((e for e in self._events if e["id"] == event_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"Event '{event_id}' not found.",
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"event": match},
                    correlation_id=request.correlation_id,
                )

        # 2. SEARCH
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_events", "find_events"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    e for e in self._events
                    if query in e["summary"].lower() or query in str(e.get("location", "")).lower() or any(query in a.lower() for a in e.get("attendees", []))
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"events": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )

        # 3. CREATE
        if request.capability == ServiceCapability.CREATE:
            if op in {"create_event", "schedule_event", "add_event"}:
                summary = request.parameters.get("summary")
                if not summary:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="Event summary is required.",
                        correlation_id=request.correlation_id,
                    )

                event = {
                    "id": f"event-{len(self._events) + 1:03d}",
                    "summary": summary,
                    "start_time": request.parameters.get("start_time", "2026-08-25T12:00:00Z"),
                    "end_time": request.parameters.get("end_time", "2026-08-25T13:00:00Z"),
                    "attendees": request.parameters.get("attendees", []),
                    "location": request.parameters.get("location", ""),
                    "status": "CONFIRMED",
                }
                self._events.append(event)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"event": event, "status": "CREATED"},
                    correlation_id=request.correlation_id,
                )

        # 4. UPDATE
        if request.capability == ServiceCapability.UPDATE:
            if op in {"update_event", "reschedule_event", "edit_event"}:
                event_id = request.parameters.get("event_id") or request.parameters.get("id")
                match = next((e for e in self._events if e["id"] == event_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"Event '{event_id}' not found to update.",
                        correlation_id=request.correlation_id,
                    )

                for k, v in request.parameters.items():
                    if k not in {"event_id", "id"}:
                        match[k] = v

                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"event": match, "status": "UPDATED"},
                    correlation_id=request.correlation_id,
                )

        # 5. DELETE
        if request.capability == ServiceCapability.DELETE:
            if op in {"delete_event", "cancel_event", "remove_event"}:
                event_id = request.parameters.get("event_id") or request.parameters.get("id")
                initial_len = len(self._events)
                self._events = [e for e in self._events if e["id"] != event_id]
                if len(self._events) < initial_len:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=True,
                        data={"deleted_id": event_id, "status": "CANCELLED"},
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=False,
                    error=f"Event '{event_id}' not found to delete.",
                    correlation_id=request.correlation_id,
                )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )
