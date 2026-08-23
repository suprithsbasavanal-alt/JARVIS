"""Hermetic Google Drive Service Connector for Cloud File Management (Phase 9.2)."""

from typing import Any
from services.base import BaseCredentialProvider
from services.connectors.common import BaseHermeticConnector, ConnectorSimulationConfig
from services.models import (
    ServiceCapability,
    ServiceMetadata,
    ServiceRequest,
    ServiceResponse,
)


class GoogleDriveConnector(BaseHermeticConnector):
    """Hermetic Google Drive adapter supporting list_files, search_files, upload_file, update_file, and delete_file."""

    def __init__(
        self,
        service_id: str = "google_drive",
        credential_provider: BaseCredentialProvider | None = None,
        simulation_config: ConnectorSimulationConfig | None = None,
    ) -> None:
        metadata = ServiceMetadata(
            service_id=service_id,
            name="Google Drive Connector",
            description="Hermetic adapter for cloud documents, spreadsheets, and file assets.",
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

        # Synthetic in-memory drive files
        self._files: list[dict[str, Any]] = [
            {
                "id": "file-001",
                "name": "Arc_Reactor_Schematics_v4.pdf",
                "mime_type": "application/pdf",
                "size_bytes": 1048576,
                "created_at": "2026-08-20T10:00:00Z",
                "owner": "tony@stark.com",
            },
            {
                "id": "file-002",
                "name": "Q3_Defense_Budget.xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size_bytes": 524288,
                "created_at": "2026-08-21T11:30:00Z",
                "owner": "pepper@stark.com",
            },
        ]

        # Default synthetic credentials
        self.credential_provider.set_credential(self.service_id, "oauth_token", "fake-gdrive-bearer-token-12345")

    async def execute(self, request: ServiceRequest) -> ServiceResponse:
        """Execute Drive operations."""
        self.validate_capability(request.capability)
        await self._apply_simulations()

        op = request.operation.lower()

        # 1. READ
        if request.capability == ServiceCapability.READ:
            if op in {"list_files", "get_files"}:
                limit = request.parameters.get("limit", 10)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"files": self._files[:limit], "count": len(self._files[:limit])},
                    correlation_id=request.correlation_id,
                )
            if op in {"read_file", "get_file", "download_file"}:
                file_id = request.parameters.get("file_id") or request.parameters.get("id")
                match = next((f for f in self._files if f["id"] == file_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"File '{file_id}' not found.",
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"file": match},
                    correlation_id=request.correlation_id,
                )

        # 2. SEARCH
        if request.capability == ServiceCapability.SEARCH:
            if op in {"search_files", "find_files"}:
                query = str(request.parameters.get("query", "")).lower()
                matches = [
                    f for f in self._files
                    if query in f["name"].lower() or query in f.get("owner", "").lower()
                ]
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"files": matches, "count": len(matches)},
                    correlation_id=request.correlation_id,
                )

        # 3. CREATE (Upload)
        if request.capability == ServiceCapability.CREATE:
            if op in {"upload_file", "create_file"}:
                name = request.parameters.get("name") or request.parameters.get("filename")
                if not name:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error="File name is required for upload.",
                        correlation_id=request.correlation_id,
                    )

                new_file = {
                    "id": f"file-{len(self._files) + 1:03d}",
                    "name": name,
                    "mime_type": request.parameters.get("mime_type", "application/octet-stream"),
                    "size_bytes": request.parameters.get("size_bytes", 1024),
                    "created_at": "2026-08-23T09:00:00Z",
                    "owner": request.parameters.get("owner", "tony@stark.com"),
                }
                self._files.append(new_file)
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"file": new_file, "status": "UPLOADED"},
                    correlation_id=request.correlation_id,
                )

        # 4. UPDATE
        if request.capability == ServiceCapability.UPDATE:
            if op in {"update_file", "rename_file"}:
                file_id = request.parameters.get("file_id") or request.parameters.get("id")
                match = next((f for f in self._files if f["id"] == file_id), None)
                if not match:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=False,
                        error=f"File '{file_id}' not found to update.",
                        correlation_id=request.correlation_id,
                    )

                for k, v in request.parameters.items():
                    if k not in {"file_id", "id"}:
                        match[k] = v

                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=True,
                    data={"file": match, "status": "UPDATED"},
                    correlation_id=request.correlation_id,
                )

        # 5. DELETE
        if request.capability == ServiceCapability.DELETE:
            if op in {"delete_file", "trash_file"}:
                file_id = request.parameters.get("file_id") or request.parameters.get("id")
                initial_len = len(self._files)
                self._files = [f for f in self._files if f["id"] != file_id]
                if len(self._files) < initial_len:
                    return ServiceResponse(
                        service_id=self.service_id,
                        operation=request.operation,
                        success=True,
                        data={"deleted_id": file_id, "status": "TRASHED"},
                        correlation_id=request.correlation_id,
                    )
                return ServiceResponse(
                    service_id=self.service_id,
                    operation=request.operation,
                    success=False,
                    error=f"File '{file_id}' not found to delete.",
                    correlation_id=request.correlation_id,
                )

        return ServiceResponse(
            service_id=self.service_id,
            operation=request.operation,
            success=False,
            error=f"Operation '{request.operation}' not supported for capability '{request.capability.value}'.",
            correlation_id=request.correlation_id,
        )
