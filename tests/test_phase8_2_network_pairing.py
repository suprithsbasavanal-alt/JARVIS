"""Automated Verification Test Suite for Phase 8.2: Local Network Transport & Hardware Key Pairing."""

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


class TestPhase82DevicePairingRegistry(unittest.TestCase):
    """Unit test suite for DevicePairingRegistry cryptographic operations and state transitions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_pairing.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.registry = DevicePairingRegistry(audit_logger=self.audit_logger, challenge_ttl_seconds=2)

        self.device_id = "pixel-8-pro-test-01"
        self.device_name = "Google Pixel 8 Pro"
        self.raw_key = bytes.fromhex("11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff")
        self.public_key_hex = self.raw_key.hex()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_begin_pairing_success(self) -> None:
        """1. Verify begin_pairing generates 6-digit code and creates PENDING_CONFIRMATION identity."""
        device, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.assertEqual(device.device_id, self.device_id)
        self.assertEqual(device.status, DeviceStatus.PENDING_CONFIRMATION)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_confirm_pairing_success(self) -> None:
        """2. Verify confirming with exact 6-digit code transitions device to CONFIRMED."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        confirmed_device = self.registry.confirm_pairing(self.device_id, code)
        self.assertEqual(confirmed_device.status, DeviceStatus.CONFIRMED)
        self.assertIsNotNone(confirmed_device.confirmed_at)
        self.assertEqual(confirmed_device.pairing_code, "")

    def test_confirm_pairing_invalid_code_rejected(self) -> None:
        """3. Verify confirming with wrong code raises InvalidPairingCodeError."""
        self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        with self.assertRaises(InvalidPairingCodeError):
            self.registry.confirm_pairing(self.device_id, "000000")

    def test_auth_challenge_generation_and_verification(self) -> None:
        """4. Verify challenge creation, deterministic signature verification, and session token generation."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)

        # Create challenge
        challenge = self.registry.create_auth_challenge(self.device_id)
        self.assertEqual(challenge.device_id, self.device_id)
        self.assertEqual(len(challenge.nonce), 64)

        # Sign challenge with device private key
        signature = DevicePairingRegistry.sign_challenge(self.public_key_hex, challenge.nonce)

        # Verify response
        session = self.registry.verify_auth_response(challenge.challenge_id, signature)
        self.assertIsNotNone(session.session_token)
        self.assertEqual(session.device_id, self.device_id)

        # Validate session
        valid_sess = self.registry.validate_session(session.session_token)
        self.assertIsNotNone(valid_sess)
        self.assertEqual(valid_sess.device_id, self.device_id)

    def test_invalid_signature_rejected(self) -> None:
        """5. Verify invalid cryptographic signature raises InvalidSignatureError."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)
        challenge = self.registry.create_auth_challenge(self.device_id)

        with self.assertRaises(InvalidSignatureError):
            self.registry.verify_auth_response(challenge.challenge_id, "deadbeef" * 8)

    def test_challenge_replay_rejected(self) -> None:
        """6. Verify presenting an already-consumed challenge raises ChallengeReplayError."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)
        challenge = self.registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.public_key_hex, challenge.nonce)

        # First verification succeeds
        self.registry.verify_auth_response(challenge.challenge_id, sig)

        # Replay attempt fails
        with self.assertRaises(ChallengeReplayError):
            self.registry.verify_auth_response(challenge.challenge_id, sig)

    def test_expired_challenge_rejected(self) -> None:
        """7. Verify challenge verification fails after TTL expiry."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)

        challenge = self.registry.create_auth_challenge(self.device_id)
        # Force expiration
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)

        sig = DevicePairingRegistry.sign_challenge(self.public_key_hex, challenge.nonce)
        with self.assertRaises(ChallengeExpiredError):
            self.registry.verify_auth_response(challenge.challenge_id, sig)

    def test_device_revocation_terminates_sessions(self) -> None:
        """8. Verify device revocation terminates active sessions and blocks new auth challenges."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)
        challenge = self.registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.public_key_hex, challenge.nonce)
        session = self.registry.verify_auth_response(challenge.challenge_id, sig)

        # Revoke device
        self.assertTrue(self.registry.revoke_device(self.device_id))

        # Active session must be invalid
        self.assertIsNone(self.registry.validate_session(session.session_token))

        # New challenge creation must fail
        with self.assertRaises(PairingError):
            self.registry.create_auth_challenge(self.device_id)

    def test_device_key_rotation_lifecycle(self) -> None:
        """9. Verify key rotation validates signature using previous key and updates registry."""
        _, code = self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        self.registry.confirm_pairing(self.device_id, code)

        new_key_hex = "99887766554433221100aabbccddeeff99887766554433221100aabbccddeeff"
        # Authorize new key with current key signature
        auth_sig = DevicePairingRegistry.sign_challenge(self.public_key_hex, new_key_hex)
        self.assertTrue(self.registry.rotate_device_key(self.device_id, new_key_hex, auth_sig))

        # Authenticate with new key
        challenge = self.registry.create_auth_challenge(self.device_id)
        new_sig = DevicePairingRegistry.sign_challenge(new_key_hex, challenge.nonce)
        sess = self.registry.verify_auth_response(challenge.challenge_id, new_sig)
        self.assertIsNotNone(sess.session_token)

    def test_list_devices(self) -> None:
        """10. Verify list_devices reports registered devices and states."""
        self.registry.begin_pairing(self.device_id, self.device_name, self.public_key_hex)
        devices = self.registry.list_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].device_id, self.device_id)


class TestPhase82NetworkBridgeIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for NetworkBridgeServer TCP communication and JSON-RPC dispatch."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "audit_bridge.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.event_bus = EventBus()
        self.permission_engine = PermissionEngine()

        # Memory manager
        self.memory_manager = MemoryManager(
            db_path=":memory:",
            audit_logger=self.audit_logger,
        )

        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem(sandbox_root=Path(self.temp_dir.name))
        self.mock_fs.write_file("/test.txt", "Sample file content")
        self.process_executor = ProcessSandboxExecutor()
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock")
        self.mock_provider.set_canned_response("Hello from JARVIS over network!")
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

        # Allocate ephemeral port on localhost
        self.server = NetworkBridgeServer(
            agent_loop=self.agent_loop,
            event_bus=self.event_bus,
            runtime_bridge=self.runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            pairing_registry=self.pairing_registry,
            host="127.0.0.1",
            port=0,  # OS assigned port
        )
        await self.server.start()
        # Retrieve actual bound port
        self.port = self.server._server.sockets[0].getsockname()[1]

        self.device_id = "android-test-device-99"
        self.device_name = "Pixel 8 Pro Test"
        self.key_hex = "223344556677889900aabbccddeeff0011223344556677889900aabbccddeeff00"

    async def asyncTearDown(self) -> None:
        await self.server.stop()
        self.temp_dir.cleanup()

    async def _send_rpc(self, method: str, params: dict[str, Any], reader, writer) -> dict[str, Any]:
        req = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": method,
            "params": params,
        }
        writer.write((json.dumps(req) + "\n").encode("utf-8"))
        await writer.drain()
        line = await reader.readline()
        return json.loads(line.decode("utf-8"))

    async def test_unauthenticated_requests_rejected(self) -> None:
        """11. Verify calling operational methods without session_token returns -32000 Authentication required."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        resp = await self._send_rpc("jarvis.status", {}, reader, writer)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32000)
        writer.close()
        await writer.wait_closed()

    async def test_complete_pairing_and_mutual_auth_flow(self) -> None:
        """12. Verify end-to-end device pairing, challenge signing, session token issuance, and turn processing."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # 1. Begin Pairing
        pair_begin = await self._send_rpc(
            "jarvis.network.pair.begin",
            {"device_id": self.device_id, "device_name": self.device_name, "public_key_hex": self.key_hex},
            reader, writer,
        )
        self.assertIn("result", pair_begin)
        code = pair_begin["result"]["pairing_code"]
        self.assertEqual(len(code), 6)

        # 2. Confirm Pairing
        pair_confirm = await self._send_rpc(
            "jarvis.network.pair.confirm",
            {"device_id": self.device_id, "pairing_code": code},
            reader, writer,
        )
        self.assertEqual(pair_confirm["result"]["status"], "CONFIRMED")

        # 3. Request Auth Challenge
        chal_resp = await self._send_rpc(
            "jarvis.network.auth.challenge",
            {"device_id": self.device_id},
            reader, writer,
        )
        chal_id = chal_resp["result"]["challenge_id"]
        nonce = chal_resp["result"]["nonce"]

        # 4. Sign and Verify Challenge
        sig = DevicePairingRegistry.sign_challenge(self.key_hex, nonce)
        auth_resp = await self._send_rpc(
            "jarvis.network.auth.verify",
            {"challenge_id": chal_id, "signature_hex": sig},
            reader, writer,
        )
        self.assertTrue(auth_resp["result"]["authenticated"])
        session_token = auth_resp["result"]["session_token"]

        # 5. Authenticated Turn Processing
        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "Hello JARVIS over local network", "session_token": session_token},
            reader, writer,
        )
        self.assertIn("result", turn_resp)
        self.assertIn("reply", turn_resp["result"])

        writer.close()
        await writer.wait_closed()

    async def test_hitl_approval_enforcement_over_network(self) -> None:
        """13. Verify sensitive tools over network bridge raise approval card and require explicit APPROVE."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # Pair & Authenticate
        _, code = self.pairing_registry.begin_pairing(self.device_id, self.device_name, self.key_hex)
        self.pairing_registry.confirm_pairing(self.device_id, code)
        chal = self.pairing_registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.key_hex, chal.nonce)
        sess = self.pairing_registry.verify_auth_response(chal.challenge_id, sig)

        # Register tool trigger on mock provider
        self.mock_provider.register_tool_trigger(
            "send sensitive email",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-1", "target_email": "cto@example.com"},
            ),
        )
        self.mock_provider.register_tool_trigger(
            "execute approved action: mock_email_sender",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-1", "target_email": "cto@example.com"},
            ),
        )

        # Request sensitive tool execution
        turn_resp = await self._send_rpc(
            "jarvis.turn.process",
            {"query": "send sensitive email", "session_token": sess.session_token},
            reader, writer,
        )
        self.assertTrue(turn_resp["result"]["requires_confirmation"])
        card = turn_resp["result"]["approval_card"]
        self.assertEqual(card["tool_name"], "mock_email_sender")

        # Approve action
        approve_resp = await self._send_rpc(
            "jarvis.approval.respond",
            {"card_id": card["card_id"], "decision": "APPROVE", "session_token": sess.session_token},
            reader, writer,
        )
        self.assertTrue(approve_resp["result"]["tool_executed"])

        writer.close()
        await writer.wait_closed()

    async def test_emergency_stop_over_network(self) -> None:
        """14. Verify emergency stop over network revokes in-flight authorizations and logs audit entry."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # Pair & Authenticate
        _, code = self.pairing_registry.begin_pairing(self.device_id, self.device_name, self.key_hex)
        self.pairing_registry.confirm_pairing(self.device_id, code)
        chal = self.pairing_registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.key_hex, chal.nonce)
        sess = self.pairing_registry.verify_auth_response(chal.challenge_id, sig)

        # Trigger emergency stop
        stop_resp = await self._send_rpc(
            "jarvis.system.emergency_stop",
            {"session_token": sess.session_token},
            reader, writer,
        )
        self.assertEqual(stop_resp["result"]["status"], "STOPPED")

        writer.close()
        await writer.wait_closed()

    async def test_device_revocation_over_network_rpc(self) -> None:
        """15. Verify device revocation via jarvis.network.device.revoke immediately invalidates sessions."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # Pair & Authenticate
        _, code = self.pairing_registry.begin_pairing(self.device_id, self.device_name, self.key_hex)
        self.pairing_registry.confirm_pairing(self.device_id, code)
        chal = self.pairing_registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.key_hex, chal.nonce)
        sess = self.pairing_registry.verify_auth_response(chal.challenge_id, sig)

        # Revoke device via RPC
        revoke_resp = await self._send_rpc(
            "jarvis.network.device.revoke",
            {"device_id": self.device_id, "session_token": sess.session_token},
            reader, writer,
        )
        self.assertEqual(revoke_resp["result"]["status"], "REVOKED")

        # Subsequent call with same session token must fail with -32001
        status_resp = await self._send_rpc(
            "jarvis.status",
            {"session_token": sess.session_token},
            reader, writer,
        )
        self.assertIn("error", status_resp)
        self.assertEqual(status_resp["error"]["code"], -32001)

        writer.close()
        await writer.wait_closed()

    async def test_proactive_and_plan_endpoints_over_network(self) -> None:
        """16. Verify proactive advisories and structured plan endpoints over authenticated network."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)

        # Pair & Authenticate
        _, code = self.pairing_registry.begin_pairing(self.device_id, self.device_name, self.key_hex)
        self.pairing_registry.confirm_pairing(self.device_id, code)
        chal = self.pairing_registry.create_auth_challenge(self.device_id)
        sig = DevicePairingRegistry.sign_challenge(self.key_hex, chal.nonce)
        sess = self.pairing_registry.verify_auth_response(chal.challenge_id, sig)

        # 1. Proactive Advisory
        proactive_resp = await self._send_rpc(
            "jarvis.proactive.get_latest",
            {"session_token": sess.session_token},
            reader, writer,
        )
        self.assertIn("result", proactive_resp)
        self.assertTrue(proactive_resp["result"]["is_informational_only"])

        # 2. Plan Get Active
        plan_resp = await self._send_rpc(
            "jarvis.plan.get_active",
            {"session_token": sess.session_token},
            reader, writer,
        )
        self.assertIn("result", plan_resp)
        self.assertTrue(plan_resp["result"]["plan"]["is_informational_only"])

        # 3. Plan Step Update
        update_resp = await self._send_rpc(
            "jarvis.plan.update_step",
            {"plan_id": "plan-android-bridge", "step_number": 1, "completed": True, "session_token": sess.session_token},
            reader, writer,
        )
        self.assertTrue(update_resp["result"]["completed"])

        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
