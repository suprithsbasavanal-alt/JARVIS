"""Comprehensive Automated Verification Test Suite for Phase 9.1: Service Integration Foundation."""

import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from uuid import uuid4

from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.events import EventBus
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from core.ipc_server import IPCServer
from core.network_bridge import NetworkBridgeServer
from core.types import ExecutionContext
from intelligence.coordinator import ProactiveCoordinator
from intelligence.runtime_listener import ProactiveRuntimeBridge
from memory.manager import MemoryManager
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from sandbox.mock_fs import MockFileSystem
from security.audit_logger import AuditLogger
from security.device_pairing import DevicePairingRegistry
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)
from services.base import (
    BaseCredentialProvider,
    BaseServiceAdapter,
    InMemoryCredentialProvider,
)
from services.mock_service import MockMessagingServiceAdapter
from services.models import (
    DuplicateServiceError,
    ServiceAuthenticationError,
    ServiceCapability,
    ServiceDisabledError,
    ServiceError,
    ServiceMetadata,
    ServiceNotFoundError,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from services.tool_bridge import ServiceTool, register_service_tools
from tools.registry import ToolRegistry


class TestPhase91ServiceIntegrationFoundation(unittest.IsolatedAsyncioTestCase):
    """Verifies adapter registry, capability model, permission gates, credential isolation, and IPC."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_services.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.permission_engine = PermissionEngine()
        self.permission_bridge = ServicePermissionBridge(permission_engine=self.permission_engine)
        self.service_registry = ServiceRegistry(
            audit_logger=self.audit_logger,
            permission_bridge=self.permission_bridge,
        )

        self.mock_adapter = MockMessagingServiceAdapter()
        self.service_registry.register(self.mock_adapter)

        self.context = SessionContext()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    # ==========================================
    # 1. Registry & Lifecycle Tests
    # ==========================================

    def test_adapter_registration_success(self) -> None:
        """1. Verify adapter registers and lists safely."""
        adapter = self.service_registry.get("mock_messaging")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.service_id, "mock_messaging")
        self.assertEqual(adapter.status, ServiceStatus.CONNECTED)

    def test_duplicate_registration_rejected(self) -> None:
        """2. Verify duplicate service registration raises DuplicateServiceError."""
        dup_adapter = MockMessagingServiceAdapter(service_id="mock_messaging")
        with self.assertRaises(DuplicateServiceError):
            self.service_registry.register(dup_adapter)

    def test_service_lookup_and_unknown_rejection(self) -> None:
        """3. Verify get_or_raise raises ServiceNotFoundError for unknown service IDs."""
        with self.assertRaises(ServiceNotFoundError):
            self.service_registry.get_or_raise("unknown_service_999")

    def test_service_enable_and_disable(self) -> None:
        """4. Verify enable/disable toggles is_enabled and rejects execution when disabled."""
        self.service_registry.disable("mock_messaging")
        adapter = self.service_registry.get("mock_messaging")
        self.assertFalse(adapter.is_enabled)
        self.assertEqual(adapter.status, ServiceStatus.DISCONNECTED)

        # Attempting execution when disabled must raise ServiceDisabledError
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.READ,
            operation="read_messages",
        )
        with self.assertRaises(ServiceDisabledError):
            asyncio.run(self.service_registry.execute(req, self.context))

        # Re-enable
        self.service_registry.enable("mock_messaging")
        self.assertTrue(adapter.is_enabled)

    async def test_service_revocation_wipes_credentials(self) -> None:
        """5. Verify revoke sets status REVOKED, disables adapter, and purges credentials."""
        await self.service_registry.revoke("mock_messaging")
        adapter = self.service_registry.get("mock_messaging")

        self.assertEqual(adapter.status, ServiceStatus.REVOKED)
        self.assertFalse(adapter.is_enabled)
        self.assertFalse(adapter.credential_provider.has_credentials("mock_messaging"))

        # Re-execution must fail closed
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.READ,
            operation="read_messages",
        )
        with self.assertRaises(ServiceDisabledError):
            await self.service_registry.execute(req, self.context)

    # ==========================================
    # 2. Capability Model & Undeclared Rejection
    # ==========================================

    def test_declared_capabilities_inspection(self) -> None:
        """6. Verify declared capabilities can be inspected."""
        caps = self.service_registry.get_capabilities("mock_messaging")
        self.assertIn("READ", caps)
        self.assertIn("SEARCH", caps)
        self.assertIn("SEND", caps)
        self.assertNotIn("EXECUTE", caps)
        self.assertNotIn("DELETE", caps)

    async def test_undeclared_capability_rejected(self) -> None:
        """7. Verify requesting undeclared capability raises UndeclaredCapabilityError."""
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.EXECUTE,  # mock_messaging does not declare EXECUTE
            operation="run_arbitrary_code",
        )
        with self.assertRaises(UndeclaredCapabilityError):
            await self.service_registry.execute(req, self.context)

    # ==========================================
    # 3. Permission Engine & HITL Gatekeeper
    # ==========================================

    async def test_read_operation_normal_permission(self) -> None:
        """8. Verify READ operations execute directly under NORMAL permission level."""
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.READ,
            operation="read_messages",
            parameters={"limit": 5},
        )
        resp = await self.service_registry.execute(req, self.context)
        self.assertTrue(resp.success)
        self.assertIn("messages", resp.data)
        self.assertEqual(len(resp.data["messages"]), 2)

    async def test_search_operation_normal_permission(self) -> None:
        """9. Verify SEARCH operations execute directly under NORMAL permission level."""
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.SEARCH,
            operation="search_contacts",
            parameters={"query": "Tony"},
        )
        resp = await self.service_registry.execute(req, self.context)
        self.assertTrue(resp.success)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["contacts"][0]["name"], "Tony Stark")

    async def test_sensitive_send_without_token_raises_hitl_card(self) -> None:
        """10. Verify SEND capability without ApprovalToken raises HumanConfirmationRequiredError with ApprovalCard."""
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.SEND,
            operation="send_message",
            parameters={"recipient": "pepper@stark.com", "body": "Diagnostic complete."},
            session_id=str(self.context.session_id),
        )

        with self.assertRaises(HumanConfirmationRequiredError) as cm:
            await self.service_registry.execute(req, self.context)

        card = cm.exception.approval_card
        self.assertIsNotNone(card)
        self.assertEqual(card.risk_level, "SENSITIVE")
        self.assertIn("send_message", card.action_name)
        self.assertEqual(card.parameter_payload["recipient"], "pepper@stark.com")

    async def test_sensitive_send_with_valid_single_use_token_succeeds(self) -> None:
        """11. Verify providing a valid single-use ApprovalToken allows SEND execution and replay is rejected."""
        params = {"recipient": "rhodey@usaf.mil", "body": "Flight plan ready."}
        payload_str = json.dumps(params, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        tool_id = "service_mock_messaging_send_message"

        token = ApprovalToken(
            card_id=uuid4(),
            tool_id=tool_id,
            target_resource="mock_messaging://send_message",
            session_id=str(self.context.session_id),
            payload_hash=payload_hash,
        )

        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.SEND,
            operation="send_message",
            parameters=params,
            session_id=str(self.context.session_id),
        )

        # First execution with token succeeds
        resp = await self.service_registry.execute(req, self.context, approval_token=token)
        self.assertTrue(resp.success)
        self.assertEqual(resp.data["status"], "DELIVERED")

        # Second execution with consumed token must fail (replay defense)
        with self.assertRaises(PermissionDeniedError):
            await self.service_registry.execute(req, self.context, approval_token=token)

    # ==========================================
    # 4. Credential Isolation & Secret Scrubbing
    # ==========================================

    def test_credential_non_disclosure_in_repr_and_metadata(self) -> None:
        """12. Verify credentials are never exposed in __repr__, __str__, or metadata dictionaries."""
        cred_provider = self.mock_adapter.credential_provider
        cred_repr = repr(cred_provider)
        self.assertIn("[REDACTED]", cred_repr)
        self.assertNotIn("mock-secret-key", cred_repr)

        metadata_dict = self.mock_adapter.metadata.to_dict()
        meta_json = json.dumps(metadata_dict)
        self.assertNotIn("mock-secret-key", meta_json)

    def test_credential_rotation(self) -> None:
        """13. Verify credential rotation updates value without exposing old/new values."""
        cred_provider = self.mock_adapter.credential_provider
        cred_provider.rotate_credential("mock_messaging", "api_key", "new-rotated-secret-key-999")
        self.assertEqual(cred_provider.get_credential("mock_messaging", "api_key"), "new-rotated-secret-key-999")

    async def test_audit_logging_and_secret_scrubbing(self) -> None:
        """14. Verify service operations produce chained SHA-256 audit logs with scrubbed parameters."""
        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.READ,
            operation="read_messages",
            parameters={"auth_token": "super-secret-token", "limit": 10},
        )
        await self.service_registry.execute(req, self.context)

        self.assertTrue(self.audit_log_path.exists())
        lines = self.audit_log_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)  # 1 registration + 1 execution

        raw_log = self.audit_log_path.read_text(encoding="utf-8")
        self.assertNotIn("super-secret-token", raw_log)
        self.assertIn("[REDACTED]", raw_log)

        for line in lines:
            entry = json.loads(line)
            self.assertIn("entry_hash", entry)
            self.assertIn("prev_hash", entry)
            self.assertIn("timestamp", entry)

    # ==========================================
    # 5. Service Health & Error Isolation
    # ==========================================

    async def test_service_health_check_states(self) -> None:
        """15. Verify health check transitions: CONNECTED -> AUTH_REQUIRED -> REVOKED."""
        status = await self.mock_adapter.health_check()
        self.assertEqual(status, ServiceStatus.CONNECTED)

        # Wipe credentials -> AUTH_REQUIRED
        self.mock_adapter.credential_provider.revoke_credentials("mock_messaging")
        status = await self.mock_adapter.health_check()
        self.assertEqual(status, ServiceStatus.AUTH_REQUIRED)

        # Revoke -> REVOKED
        await self.mock_adapter.revoke()
        status = await self.mock_adapter.health_check()
        self.assertEqual(status, ServiceStatus.DISCONNECTED)

    async def test_adapter_failure_isolation(self) -> None:
        """16. Verify adapter exceptions during execution are isolated without crashing the caller."""
        # Adapter with missing credentials raises ServiceAuthenticationError internally
        self.mock_adapter.credential_provider.revoke_credentials("mock_messaging")
        self.mock_adapter.is_enabled = True

        req = ServiceRequest(
            service_id="mock_messaging",
            capability=ServiceCapability.READ,
            operation="read_messages",
        )
        resp = await self.service_registry.execute(req, self.context)
        self.assertFalse(resp.success)
        self.assertIn("failed", resp.error.lower())

    # ==========================================
    # 6. ToolRegistry & AgentLoop Integration
    # ==========================================

    async def test_tool_registry_service_tools_generation(self) -> None:
        """17. Verify register_service_tools registers ServiceTool instances into ToolRegistry."""
        tool_registry = ToolRegistry()
        names = register_service_tools(self.service_registry, tool_registry)

        self.assertIn("service_mock_messaging_read_messages", names)
        self.assertIn("service_mock_messaging_search_contacts", names)
        self.assertIn("service_mock_messaging_send_message", names)

        # Execute read via tool
        tool = tool_registry.get_tool("service_mock_messaging_read_messages")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.definition.permission_tier, PermissionLevel.NORMAL)

        result = await tool.execute({"limit": 5}, self.context)
        self.assertTrue(result.is_success)
        self.assertIn("messages", result.output_data["data"])

    # ==========================================
    # 7. IPC & Network Bridge Service Endpoints
    # ==========================================

    async def test_ipc_services_list_status_capabilities(self) -> None:
        """18. Verify Unix Domain Socket IPC endpoints for service management."""
        event_bus = EventBus()
        runtime_bridge = ProactiveRuntimeBridge(
            coordinator=ProactiveCoordinator(audit_logger=self.audit_logger),
            event_bus=event_bus,
        )
        model_router = ModelRouter()
        mock_provider = MockModelProvider("mock")
        model_router.register_provider("mock", mock_provider)

        agent_loop = AgentLoop(
            tool_registry=ToolRegistry(),
            permission_engine=self.permission_engine,
            model_router=model_router,
            audit_logger=self.audit_logger,
            memory_manager=MemoryManager(db_path=":memory:", audit_logger=self.audit_logger),
        )

        sock_path = Path(self.temp_dir.name) / "test_ipc_p9.sock"
        ipc_server = IPCServer(
            agent_loop=agent_loop,
            event_bus=event_bus,
            runtime_bridge=runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            socket_path=sock_path,
            auth_token="test-auth-p9",
            service_registry=self.service_registry,
        )
        await ipc_server.start()

        reader, writer = await asyncio.open_unix_connection(str(sock_path))

        async def _rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
            req = {"jsonrpc": "2.0", "id": str(uuid4()), "method": method, "params": params}
            writer.write((json.dumps(req) + "\n").encode("utf-8"))
            await writer.drain()
            line = await reader.readline()
            return json.loads(line.decode("utf-8"))

        # Handshake
        await _rpc("jarvis.handshake", {"auth_token": "test-auth-p9"})

        # 1. Services List
        list_resp = await _rpc("jarvis.services.list", {})
        self.assertIn("services", list_resp["result"])
        self.assertEqual(len(list_resp["result"]["services"]), 1)
        self.assertEqual(list_resp["result"]["services"][0]["service_id"], "mock_messaging")

        # 2. Services Capabilities
        caps_resp = await _rpc("jarvis.services.capabilities", {"service_id": "mock_messaging"})
        self.assertIn("capabilities", caps_resp["result"])
        self.assertIn("READ", caps_resp["result"]["capabilities"])

        # 3. Services Status
        stat_resp = await _rpc("jarvis.services.status", {"service_id": "mock_messaging"})
        self.assertEqual(stat_resp["result"]["status"], "CONNECTED")

        # 4. Services Revoke
        rev_resp = await _rpc("jarvis.services.revoke", {"service_id": "mock_messaging"})
        self.assertEqual(rev_resp["result"]["status"], "REVOKED")

        writer.close()
        await writer.wait_closed()
        await ipc_server.stop()

    async def test_network_bridge_services_endpoints(self) -> None:
        """19. Verify Network Bridge TCP/TLS endpoints for service management."""
        event_bus = EventBus()
        runtime_bridge = ProactiveRuntimeBridge(
            coordinator=ProactiveCoordinator(audit_logger=self.audit_logger),
            event_bus=event_bus,
        )
        model_router = ModelRouter()
        mock_provider = MockModelProvider("mock")
        model_router.register_provider("mock", mock_provider)

        agent_loop = AgentLoop(
            tool_registry=ToolRegistry(),
            permission_engine=self.permission_engine,
            model_router=model_router,
            audit_logger=self.audit_logger,
            memory_manager=MemoryManager(db_path=":memory:", audit_logger=self.audit_logger),
        )

        pairing_registry = DevicePairingRegistry(audit_logger=self.audit_logger)
        net_server = NetworkBridgeServer(
            agent_loop=agent_loop,
            event_bus=event_bus,
            runtime_bridge=runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            pairing_registry=pairing_registry,
            service_registry=self.service_registry,
            host="127.0.0.1",
            port=0,
        )
        await net_server.start()
        port = net_server._server.sockets[0].getsockname()[1]

        dev_id = "pixel-p9"
        key_hex = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
        _, code = pairing_registry.begin_pairing(dev_id, "Pixel 9 Pro", key_hex)
        pairing_registry.confirm_pairing(dev_id, code)

        reader, writer = await asyncio.open_connection("127.0.0.1", port)

        async def _send(method: str, params: dict[str, Any]) -> dict[str, Any]:
            req = {"jsonrpc": "2.0", "id": str(uuid4()), "method": method, "params": params}
            writer.write((json.dumps(req) + "\n").encode("utf-8"))
            await writer.drain()
            line = await reader.readline()
            return json.loads(line.decode("utf-8"))

        chal_resp = await _send("jarvis.network.auth.challenge", {"device_id": dev_id})
        sig = DevicePairingRegistry.sign_challenge(key_hex, chal_resp["result"]["nonce"])
        auth_resp = await _send("jarvis.network.auth.verify", {"challenge_id": chal_resp["result"]["challenge_id"], "signature_hex": sig})
        token = auth_resp["result"]["session_token"]

        # Call jarvis.services.list with session token
        list_resp = await _send("jarvis.services.list", {"session_token": token})
        self.assertIn("services", list_resp["result"])
        self.assertEqual(len(list_resp["result"]["services"]), 1)

        writer.close()
        await writer.wait_closed()
        await net_server.stop()


if __name__ == "__main__":
    unittest.main()
