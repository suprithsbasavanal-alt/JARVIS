"""Hermetic GitHub Service Connector for Repository and Issue Tracking (Phase 9.2)."""

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


class GitHubConnector(BaseHermeticConnector):
    """Hermetic & Production-ready GitHub adapter supporting list_issues, search_issues, create_issue, update_issue, and close_issue."""

    def __init__(
        self,
        service_id: str = "github",
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
        transport: BaseHttpTransport | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="GitHub Version Control & Issues Connector",
            description="Hermetic adapter for repositories, pull requests, issues, and commit metadata.",
            capabilities=frozenset({
                ServiceCapability.READ,
                ServiceCapability.SEARCH,
                ServiceCapability.CREATE,
                ServiceCapability.UPDATE,
                ServiceCapability.DELETE,
            }),
            version="1.0.0",
            auth_type="PERSONAL_ACCESS_TOKEN",
        )
        super().__init__(
            metadata=metadata,
            credential_provider=credential_provider,
            simulation_config=simulation_config,
            transport=transport,
        )

        # Synthetic in-memory repository state
        self._issues: list[dict[str, Any]] = [
            {
                "number": 101,
                "title": "Optimize sub-second TTFT for edge reasoning models",
                "body": "Profile KV cache memory bandwidth on Apple Silicon M-series.",
                "state": "open",
                "labels": ["performance", "phase-11"],
                "author": "suprith",
            },
            {
                "number": 102,
                "title": "Enforce biometric authorization on sensitive tool calls",
                "body": "Completed in Phase 8.4 via BiometricPrompt.",
                "state": "closed",
                "labels": ["security", "phase-8"],
                "author": "suprith",
            },
        ]
        self._pull_requests: list[dict[str, Any]] = []

        # Default synthetic credentials
        self.credential_provider.set_credential(self.service_id, "pat_token", "ghp_fake-github-pat-token-12345")

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute GitHub operations."""
        self.validate_capability(request.capability)
        await self._apply_simulations()

        op = request.operation.lower()

        # 1. READ
        if request.capability == ServiceCapability.READ:
            if op in {"list_issues", "get_issues", "read_repo"}:
                state_filter = request.parameters.get("state")
                filtered = [i for i in self._issues if not state_filter or i["state"] == state_filter]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"issues": filtered, "count": len(filtered)},
                    correlation_id=request.correlation_id,
                )
            if op in {"get_issue", "issue_details"}:
                issue_num = request.parameters.get("issue_number") or request.parameters.get("number")
                match = next((i for i in self._issues if i["number"] == int(issue_num or 0)), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"GitHub Issue #{issue_num} not found.",
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"issue": match},
                    correlation_id=request.correlation_id,
                )

        # 2. SEARCH
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_issues", "search_code"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    i for i in self._issues
                    if query in i["title"].lower() or query in i["body"].lower() or any(query in l.lower() for l in i.get("labels", []))
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"issues": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )

        # 3. CREATE
        if request.capability == ServiceCapability.CREATE:
            if op in {"create_issue", "open_issue"}:
                title = request.parameters.get("title")
                body = request.parameters.get("body", "")
                if not title:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="Issue title is required.",
                        correlation_id=request.correlation_id,
                    )

                new_issue = {
                    "number": len(self._issues) + 101,
                    "title": title,
                    "body": body,
                    "state": "open",
                    "labels": request.parameters.get("labels", ["enhancement"]),
                    "author": "jarvis-bot",
                }
                self._issues.append(new_issue)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"issue": new_issue, "status": "OPENED"},
                    correlation_id=request.correlation_id,
                )

        # 4. UPDATE
        if request.capability == ServiceCapability.UPDATE:
            if op in {"update_issue", "edit_issue"}:
                issue_num = request.parameters.get("issue_number") or request.parameters.get("number")
                match = next((i for i in self._issues if i["number"] == int(issue_num or 0)), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"GitHub Issue #{issue_num} not found to update.",
                        correlation_id=request.correlation_id,
                    )

                for k, v in request.parameters.items():
                    if k not in {"issue_number", "number"}:
                        match[k] = v

                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"issue": match, "status": "UPDATED"},
                    correlation_id=request.correlation_id,
                )

        # 5. DELETE (Close issue / delete comment)
        if request.capability == ServiceCapability.DELETE:
            if op in {"close_issue", "delete_comment"}:
                issue_num = request.parameters.get("issue_number") or request.parameters.get("number")
                match = next((i for i in self._issues if i["number"] == int(issue_num or 0)), None)
                if match:
                    match["state"] = "closed"
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=True,
                        data={"number": match["number"], "status": "CLOSED"},
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=False,
                    error=f"GitHub Issue #{issue_num} not found to close.",
                    correlation_id=request.correlation_id,
                )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )
