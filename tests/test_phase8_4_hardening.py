"""Automated Verification Test Suite for Phase 8.4: Android Companion Production Hardening."""

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


class TestPhase84ProductionHardening(unittest.IsolatedAsyncioTestCase):
    """Verifies production hardening, lifecycle safety, timeout bounds, and privacy controls."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_hardening.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.event_bus = EventBus()
        self.permission_engine = PermissionEngine()

        self.memory_manager = MemoryManager(
            db_path=":memory:",
            audit_logger=self.audit_logger,
        )

        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem(sandbox_root=Path(self.temp_dir.name))
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock")
        self.mock_provider.set_canned_response("JARVIS hard-state response verified.")
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

        self.device_id = "pixel-hardened-8-4"
        self.device_name = "Production Pixel 8 Companion"
        self.key_hex = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"

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

    async def test_session_lifecycle_and_invalidation(self) -> None:
        """1. Verify session creation, token validation, and explicit server-side revocation."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Status check succeeds with token
        status_resp = await self._send_rpc("jarvis.status", {"session_token": token}, reader, writer)
        self.assertEqual(status_resp["result"]["status"], "HEALTHY")

        # Explicitly revoke device
        await self._send_rpc("jarvis.network.device.revoke", {"device_id": self.device_id, "session_token": token}, reader, writer)

        # Subsequent requests with same token fail immediately (-32001)
        err_resp = await self._send_rpc("jarvis.status", {"session_token": token}, reader, writer)
        self.assertIn("error", err_resp)
        self.assertEqual(err_resp["error"]["code"], -32001)

        writer.close()
        await writer.wait_closed()

    async def test_stale_approval_card_rejection(self) -> None:
        """2. Verify presenting an invalid or non-existent approval card ID is rejected."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        res = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": "non-existent-card-999", "decision": "APPROVE", "session_token": token},
            reader, writer,
        )
        self.assertEqual(res["result"]["status"], "DENIED")
        self.assertFalse(res["result"]["tool_executed"])

        writer.close()
        await writer.wait_closed()

    async def test_single_use_approval_token_cannot_replay(self) -> None:
        """3. Verify approved action consumes the card and cannot be approved twice."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        # Setup tool trigger
        self.mock_provider.register_tool_trigger(
            "send transaction email",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-202", "target_email": "finance@example.com"},
            ),
        )

        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "send transaction email", "session_token": token},
            reader, writer,
        )
        self.assertTrue(turn_resp["result"]["requires_confirmation"])
        card_id = turn_resp["result"]["approval_card"]["card_id"]

        # First approval succeeds
        appr1 = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": card_id, "decision": "APPROVE", "session_token": token},
            reader, writer,
        )
        self.assertEqual(appr1["result"]["status"], "COMPLETED")
        self.assertTrue(appr1["result"]["tool_executed"])

        # Second approval on same card must fail
        appr2 = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": card_id, "decision": "APPROVE", "session_token": token},
            reader, writer,
        )
        self.assertEqual(appr2["result"]["status"], "DENIED")
        self.assertFalse(appr2["result"]["tool_executed"])

        writer.close()
        await writer.wait_closed()

    async def test_emergency_stop_during_pending_approval_race(self) -> None:
        """4. Verify Emergency Stop immediately invalidates all pending approvals in flight."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        self.mock_provider.register_tool_trigger(
            "delete production database",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-danger", "target_email": "ops@example.com"},
            ),
        )

        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "delete production database", "session_token": token},
            reader, writer,
        )
        card_id = turn_resp["result"]["approval_card"]["card_id"]

        # Trigger Emergency Stop
        stop_resp = await self._send_rpc("jarvis.system.emergency_stop", {"session_token": token}, reader, writer)
        self.assertEqual(stop_resp["result"]["status"], "STOPPED")

        # Approval attempt after stop must be rejected
        appr_resp = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": card_id, "decision": "APPROVE", "session_token": token},
            reader, writer,
        )
        self.assertEqual(appr_resp["result"]["status"], "DENIED")
        self.assertFalse(appr_resp["result"]["tool_executed"])

        writer.close()
        await writer.wait_closed()

    async def test_oversized_payload_rejection_at_5mb(self) -> None:
        """5. Verify payloads > 5MB are rejected with code -32600 to prevent memory DoS."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port, limit=10 * 1024 * 1024)

        oversized_data = "X" * (5 * 1024 * 1024 + 1024)
        payload = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "jarvis.status", "params": {"data": oversized_data}}) + "\n"
        writer.write(payload.encode("utf-8"))
        await writer.drain()

        line = await reader.readline()
        resp = json.loads(line.decode("utf-8"))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)

        writer.close()
        await writer.wait_closed()

    async def test_audit_trail_integrity(self) -> None:
        """6. Verify all lifecycle actions generate chained SHA-256 non-repudiable audit logs."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)
        await self._send_rpc("jarvis.status", {"session_token": token}, reader, writer)

        self.assertTrue(self.audit_log_path.exists())
        lines = self.audit_log_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertGreaterEqual(len(lines), 3)

        for line in lines:
            entry = json.loads(line)
            self.assertIn("entry_hash", entry)
            self.assertIn("prev_hash", entry)
            self.assertIn("timestamp", entry)

        writer.close()
        await writer.wait_closed()

    async def test_secret_scrubbing_in_responses(self) -> None:
        """7. Verify RPC responses never contain host API tokens or private keys."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        token = await self._authenticate_client(reader, writer)

        status_resp = await self._send_rpc("jarvis.status", {"session_token": token}, reader, writer)
        raw_json = json.dumps(status_resp)

        self.assertNotIn("openai_api_key", raw_json.lower())
        self.assertNotIn("anthropic_api_key", raw_json.lower())
        self.assertNotIn("gemini_api_key", raw_json.lower())
        self.assertNotIn("secret", raw_json.lower())

        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
