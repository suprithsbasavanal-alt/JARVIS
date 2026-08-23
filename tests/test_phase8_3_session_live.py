"""Automated Verification Test Suite for Phase 8.3: Android ↔ macOS Secure Session & Live JARVIS Communication."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from uuid import uuid4

from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.events import EventBus
from core.network_bridge import NetworkBridgeServer
from intelligence.coordinator import ProactiveCoordinator
from intelligence.runtime_listener import ProactiveRuntimeBridge
from memory.manager import MemoryManager
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from model_routing.schemas import ToolCallDefinition
from sandbox.mock_fs import MockFileSystem
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.device_pairing import (
    ChallengeExpiredError,
    ChallengeReplayError,
    DeviceNotFoundError,
    DevicePairingRegistry,
    DeviceRevokedError,
    DeviceStatus,
    InvalidPairingCodeError,
    InvalidSignatureError,
    PairingError,
)
from security.permissions import PermissionEngine
from tools.mock_tools import MockFileReaderTool, MockEmailSenderTool
from tools.registry import ToolRegistry


class TestPhase83LiveSessionLifecycle(unittest.IsolatedAsyncioTestCase):
    """End-to-end integration test suite verifying secure session lifecycle, JSON-RPC communication, and HITL."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_session_live.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.event_bus = EventBus()
        self.permission_engine = PermissionEngine()

        # In-memory memory manager
        self.memory_manager = MemoryManager(
            db_path=":memory:",
            audit_logger=self.audit_logger,
        )

        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem(sandbox_root=Path(self.temp_dir.name))
        self.mock_fs.write_file("/test_document.md", "# Sample Document")
        self.process_executor = ProcessSandboxExecutor()
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock")
        self.mock_provider.set_canned_response("JARVIS core has processed your session request.")
        self.model_router.register_provider("mock", self.mock_provider)

        self.proactive_coordinator = ProactiveCoordinator(
            default_cooldown_seconds=1.0,
            audit_logger=self.audit_logger,
        )
        self.runtime_bridge = ProactiveRuntimeBridge(
            coordinator=self.proactive_coordinator,
            event_bus=self.event_bus,
        )

        self.agent_loop = AgentLoop(
            tool_registry=self.tool_registry,
            permission_engine=self.permission_engine,
            model_router=self.model_router,
            audit_logger=self.audit_logger,
            memory_manager=self.memory_manager,
        )

        self.pairing_registry = DevicePairingRegistry(audit_logger=self.audit_logger)

        # Allocate ephemeral port on loopback
        self.server = NetworkBridgeServer(
            agent_loop=self.agent_loop,
            event_bus=self.event_bus,
            runtime_bridge=self.runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            pairing_registry=self.pairing_registry,
            host="127.0.0.1",
            port=0,
        )
        await self.server.start()
        self.port = self.server._server.sockets[0].getsockname()[1]

        # Register and confirm test companion device
        self.device_id = "pixel-companion-8-3"
        self.device_name = "Google Pixel 8 Pro Companion"
        self.key_hex = "3344556677889900aabbccddeeff0011223344556677889900aabbccddeeff0011"

        _, code = self.pairing_registry.begin_pairing(self.device_id, self.device_name, self.key_hex)
        self.pairing_registry.confirm_pairing(self.device_id, code)

    async def asyncTearDown(self) -> None:
        await self.server.stop()
        self.temp_dir.cleanup()

    async def _send_rpc(self, method: str, params: dict[str, Any], reader, writer, custom_id: str | None = None) -> dict[str, Any]:
        req_id = custom_id or str(uuid4())
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        writer.write((json.dumps(req) + "\n").encode("utf-8"))
        await writer.drain()
        line = await reader.readline()
        if not line:
            raise ConnectionError("Server closed connection.")
        return json.loads(line.decode("utf-8"))

    async def _authenticate_client(self, reader, writer) -> str:
        chal_resp = await self._send_rpc("jarvis.network.auth.challenge", {"device_id": self.device_id}, reader, writer)
        chal_id = chal_resp["result"]["challenge_id"]
        nonce = chal_resp["result"]["nonce"]

        sig = DevicePairingRegistry.sign_challenge(self.key_hex, nonce)
        auth_resp = await self._send_rpc("jarvis.network.auth.verify", {"challenge_id": chal_id, "signature_hex": sig}, reader, writer)
        return auth_resp["result"]["session_token"]

    async def test_session_create_and_get_lifecycle(self) -> None:
        """1. Verify authenticated session creation, session retrieval, and user context binding."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Create session
        create_resp = await self._send_rpc(
            "jarvis.session.create",
            {"user_display_name": "Suprith Basavanal", "session_token": token},
            reader, writer,
        )
        self.assertIn("result", create_resp)
        session_id = create_resp["result"]["session_id"]
        self.assertEqual(create_resp["result"]["user_display_name"], "Suprith Basavanal")

        # Get session
        get_resp = await self._send_rpc(
            "jarvis.session.get",
            {"session_id": session_id, "session_token": token},
            reader, writer,
        )
        self.assertIn("result", get_resp)
        self.assertEqual(get_resp["result"]["session_id"], session_id)
        self.assertEqual(get_resp["result"]["user_display_name"], "Suprith Basavanal")

        writer.close()
        await writer.wait_closed()

    async def test_heartbeat_keepalive(self) -> None:
        """2. Verify periodic heartbeat endpoint reports ALIVE and active daemon counts."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        hb_resp = await self._send_rpc(
            "jarvis.heartbeat",
            {"session_token": token},
            reader, writer,
        )
        self.assertIn("result", hb_resp)
        self.assertEqual(hb_resp["result"]["status"], "ALIVE")
        self.assertIn("timestamp", hb_resp["result"])
        self.assertGreaterEqual(hb_resp["result"]["paired_devices"], 1)

        writer.close()
        await writer.wait_closed()

    async def test_conversation_turn_round_trip(self) -> None:
        """3. Verify live turn round trip through AgentLoop and model provider."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "Status report please", "session_token": token},
            reader, writer,
        )
        self.assertIn("result", turn_resp)
        self.assertEqual(turn_resp["result"]["status"], "COMPLETED")
        self.assertFalse(turn_resp["result"]["requires_confirmation"])
        self.assertIn("JARVIS core", turn_resp["result"]["reply"])

        writer.close()
        await writer.wait_closed()

    async def test_status_synchronization(self) -> None:
        """4. Verify status synchronization reports healthy system state and version 0.8.3."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        status_resp = await self._send_rpc(
            "jarvis.status",
            {"session_token": token},
            reader, writer,
        )
        self.assertIn("result", status_resp)
        self.assertEqual(status_resp["result"]["status"], "HEALTHY")
        self.assertEqual(status_resp["result"]["version"], "0.8.3")
        self.assertEqual(status_resp["result"]["agent_state"], "IDLE")

        writer.close()
        await writer.wait_closed()

    async def test_proactive_advisory_informational_enforcement(self) -> None:
        """5. Verify proactive advisories strictly preserve is_informational_only = true."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        proactive_resp = await self._send_rpc(
            "jarvis.proactive.get_latest",
            {"session_token": token},
            reader, writer,
        )
        self.assertIn("result", proactive_resp)
        self.assertTrue(proactive_resp["result"]["is_informational_only"])
        self.assertFalse(proactive_resp["result"]["is_executable_directly"])

        writer.close()
        await writer.wait_closed()

    async def test_plan_synchronization_and_step_toggle(self) -> None:
        """6. Verify structured plan retrieval and persistent step toggle over live connection."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # 1. Fetch active plan
        plan_resp = await self._send_rpc(
            "jarvis.plan.get_active",
            {"session_token": token},
            reader, writer,
        )
        self.assertIn("result", plan_resp)
        plan = plan_resp["result"]["plan"]
        self.assertEqual(plan["plan_id"], "plan-android-bridge")

        # 2. Toggle step
        update_resp = await self._send_rpc(
            "jarvis.plan.update_step",
            {"plan_id": plan["plan_id"], "step_number": 2, "completed": True, "session_token": token},
            reader, writer,
        )
        self.assertIn("result", update_resp)
        self.assertTrue(update_resp["result"]["completed"])

        writer.close()
        await writer.wait_closed()

    async def test_hitl_approval_and_denial_flow(self) -> None:
        """7. Verify sensitive tool execution triggers ApprovalCard and denial cancels execution."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Register tool triggers on mock provider
        self.mock_provider.register_tool_trigger(
            "send sensitive email",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-99", "target_email": "owner@example.com"},
            ),
        )

        # Trigger sensitive action
        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "send sensitive email", "session_token": token},
            reader, writer,
        )
        self.assertTrue(turn_resp["result"]["requires_confirmation"])
        card = turn_resp["result"]["approval_card"]
        self.assertEqual(card["tool_name"], "mock_email_sender")

        # Deny confirmation
        deny_resp = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": card["card_id"], "decision": "DENY", "session_token": token},
            reader, writer,
        )
        self.assertEqual(deny_resp["result"]["status"], "DENIED")
        self.assertFalse(deny_resp["result"]["tool_executed"])

        writer.close()
        await writer.wait_closed()

    async def test_emergency_stop_kills_in_flight_approvals(self) -> None:
        """8. Verify emergency stop revokes pending approvals and logs kill-switch audit event."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Trigger sensitive action to create pending approval
        self.mock_provider.register_tool_trigger(
            "send urgent email",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-101", "target_email": "board@example.com"},
            ),
        )
        await self._send_rpc(
            "jarvis.turn.process",
            {"query": "send urgent email", "session_token": token},
            reader, writer,
        )

        # Trigger Emergency Stop
        stop_resp = await self._send_rpc(
            "jarvis.system.emergency_stop",
            {"session_token": token},
            reader, writer,
        )
        self.assertEqual(stop_resp["result"]["status"], "STOPPED")
        self.assertGreaterEqual(stop_resp["result"]["revoked_approvals"], 1)

        writer.close()
        await writer.wait_closed()

    async def test_revoked_device_rejected(self) -> None:
        """9. Verify device revocation terminates active sessions and rejects subsequent calls with -32001."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Revoke device
        revoke_resp = await self._send_rpc(
            "jarvis.network.device.revoke",
            {"device_id": self.device_id, "session_token": token},
            reader, writer,
        )
        self.assertEqual(revoke_resp["result"]["status"], "REVOKED")

        # Subsequent call with same session token fails
        status_resp = await self._send_rpc(
            "jarvis.status",
            {"session_token": token},
            reader, writer,
        )
        self.assertIn("error", status_resp)
        self.assertEqual(status_resp["error"]["code"], -32001)

        writer.close()
        await writer.wait_closed()

    async def test_secret_non_disclosure(self) -> None:
        """10. Verify status and response dictionaries never disclose host secrets or private keys."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        status_resp = await self._send_rpc(
            "jarvis.status",
            {"session_token": token},
            reader, writer,
        )
        serialized = json.dumps(status_resp)
        self.assertNotIn("api_key", serialized.lower())
        self.assertNotIn("secret_key", serialized.lower())
        self.assertNotIn("private_key", serialized.lower())

        writer.close()
        await writer.wait_closed()

    async def test_malformed_json_and_unknown_method_rejection(self) -> None:
        """11. Verify malformed JSON returns -32700 and unknown methods return -32601."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # Malformed raw JSON
        writer.write(b"NOT_A_VALID_JSON_STRING\n")
        await writer.drain()
        line = await reader.readline()
        resp = json.loads(line.decode("utf-8"))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32700)

        # Unknown method
        unknown_resp = await self._send_rpc("jarvis.unknown.method", {}, reader, writer)
        self.assertIn("error", unknown_resp)
        self.assertEqual(unknown_resp["error"]["code"], -32601)

        writer.close()
        await writer.wait_closed()

    async def test_oversized_payload_rejection(self) -> None:
        """12. Verify payloads exceeding 5 MB are rejected with code -32600 to prevent DoS."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port, limit=10 * 1024 * 1024)

        oversized_data = "A" * (6 * 1024 * 1024)
        oversized_payload = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "jarvis.status", "params": {"data": oversized_data}}) + "\n"
        writer.write(oversized_payload.encode("utf-8"))
        await writer.drain()

        line = await reader.readline()
        resp = json.loads(line.decode("utf-8"))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)

        writer.close()
        await writer.wait_closed()

    async def test_request_id_correlation(self) -> None:
        """13. Verify server preserves exact request id in response envelope for correlation matching."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        custom_id = "req-correlation-id-9988"
        resp = await self._send_rpc(
            "jarvis.status",
            {"session_token": token},
            reader, writer,
            custom_id=custom_id,
        )
        self.assertEqual(resp["id"], custom_id)

        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
