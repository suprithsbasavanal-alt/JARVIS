"""Regression and Integration Tests for JARVIS Desktop Conversation Bridge and IPC."""

import asyncio
import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
import urllib.error

from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.events import EventBus
from core.ipc_server import IPCServer
from core.types import ExecutionContext
from desktop.daemon import JarvisDesktopDaemon
from intelligence.coordinator import ProactiveCoordinator
from intelligence.runtime_listener import ProactiveRuntimeBridge
from memory.manager import MemoryManager
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from model_routing.schemas import ToolCallDefinition
from sandbox.mock_fs import MockFileSystem
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.permissions import PermissionEngine
from tools.mock_tools import MockEmailSenderTool, MockFileReaderTool
from tools.registry import ToolRegistry


class TestDesktopConversationBridge(unittest.IsolatedAsyncioTestCase):
    """Verify end-to-end conversation path, error propagation, session management, and HTTP dev bridge."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.socket_path = Path(self.temp_dir.name) / "test_bridge.sock"
        self.auth_token = "test-bridge-token-xyz"
        self.http_port = 8799

        # Security & Subsystems
        self.audit_logger = AuditLogger()
        self.permission_engine = PermissionEngine()
        self.event_bus = EventBus()
        self.memory_manager = MemoryManager(db_path=":memory:", audit_logger=self.audit_logger)

        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem(sandbox_root=Path(self.temp_dir.name))
        self.process_executor = ProcessSandboxExecutor()
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock")
        self.mock_provider.set_canned_response("I am JARVIS, ready to assist.")
        self.model_router.register_provider("mock", self.mock_provider)
        self.model_router.register_provider("mock-primary", self.mock_provider)

        self.proactive_coordinator = ProactiveCoordinator(audit_logger=self.audit_logger)
        self.runtime_bridge = ProactiveRuntimeBridge(coordinator=self.proactive_coordinator, event_bus=self.event_bus)

        self.agent_loop = AgentLoop(
            model_router=self.model_router,
            tool_registry=self.tool_registry,
            permission_engine=self.permission_engine,
            sandbox_executor=self.process_executor,
            audit_logger=self.audit_logger,
            memory_manager=self.memory_manager,
        )

        self.ipc_server = IPCServer(
            agent_loop=self.agent_loop,
            event_bus=self.event_bus,
            runtime_bridge=self.runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            socket_path=self.socket_path,
            auth_token=self.auth_token,
        )
        await self.ipc_server.start()

        # Start HTTP bridge on ephemeral port
        self.daemon = JarvisDesktopDaemon(socket_path=self.socket_path, auth_token=self.auth_token)
        self.daemon.ipc_server = self.ipc_server
        self.http_server = await asyncio.start_server(
            self.daemon._handle_http_client,
            host="127.0.0.1",
            port=0,
        )
        self.http_port = self.http_server.sockets[0].getsockname()[1]

    async def asyncTearDown(self) -> None:
        if self.http_server:
            self.http_server.close()
            await self.http_server.wait_closed()
        await self.ipc_server.stop()
        self.temp_dir.cleanup()

    async def _http_rpc(self, method: str, params: dict, auth_token: str | None = None) -> dict:
        """Helper to invoke JSON-RPC over the HTTP dev bridge asynchronously."""
        token = auth_token if auth_token is not None else self.auth_token
        req_data = json.dumps({
            "jsonrpc": "2.0",
            "id": "test-http-req-1",
            "method": method,
            "params": params,
        })

        reader, writer = await asyncio.open_connection("127.0.0.1", self.http_port)
        http_req = (
            f"POST /rpc HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.http_port}\r\n"
            f"Content-Type: application/json\r\n"
            f"X-Jarvis-Auth-Token: {token}\r\n"
            f"Content-Length: {len(req_data.encode('utf-8'))}\r\n"
            f"Connection: close\r\n\r\n"
            f"{req_data}"
        )
        writer.write(http_req.encode("utf-8"))
        await writer.drain()

        # Parse HTTP status line and headers
        status_line = await reader.readline()
        headers: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n" or line == b"\n":
                break
            h_str = line.decode("utf-8").strip()
            if ":" in h_str:
                k, v = h_str.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_length = int(headers.get("content-length", 0))
        body = await reader.readexactly(content_length) if content_length > 0 else b""
        writer.close()
        await writer.wait_closed()
        return json.loads(body.decode("utf-8"))

    async def _http_get(self, path: str) -> dict:
        """Helper for HTTP GET."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.http_port)
        http_req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.http_port}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(http_req.encode("utf-8"))
        await writer.drain()

        # Parse HTTP status line and headers
        status_line = await reader.readline()
        headers: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n" or line == b"\n":
                break
            h_str = line.decode("utf-8").strip()
            if ":" in h_str:
                k, v = h_str.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_length = int(headers.get("content-length", 0))
        body = await reader.readexactly(content_length) if content_length > 0 else b""
        writer.close()
        await writer.wait_closed()
        return json.loads(body.decode("utf-8"))

    # =========================================================================
    # Test Cases
    # =========================================================================

    async def test_no_empty_response_on_turn_process(self) -> None:
        """Regression test: verify turn processing never produces empty response or silent {}."""
        # 1. Create Session
        create_resp = await self._http_rpc("jarvis.session.create", {"user_name": "Suprith"})
        self.assertIn("result", create_resp)
        session_id = create_resp["result"]["session_id"]
        self.assertTrue(len(session_id) > 0)

        # 2. Process Turn
        turn_resp = await self._http_rpc("jarvis.turn.process", {
            "session_id": session_id,
            "query": "Hello JARVIS, status report please",
        })
        self.assertIn("result", turn_resp)
        result = turn_resp["result"]

        # Ensure response is non-empty and well-typed
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["session_id"], session_id)
        self.assertFalse(result["requires_confirmation"])
        self.assertIsNotNone(result.get("reply"))
        self.assertGreater(len(result["reply"].strip()), 0)
        self.assertEqual(result["reply"], "I am JARVIS, ready to assist.")

    async def test_session_id_propagation_and_persistence(self) -> None:
        """Verify session ID is explicitly created, returned, and preserved across multiple turns."""
        create_resp = await self._http_rpc("jarvis.session.create", {"user_name": "Suprith Basavanal"})
        session_id = create_resp["result"]["session_id"]

        # First turn
        resp1 = await self._http_rpc("jarvis.turn.process", {"session_id": session_id, "query": "Turn 1"})
        self.assertEqual(resp1["result"]["session_id"], session_id)

        # Second turn
        resp2 = await self._http_rpc("jarvis.turn.process", {"session_id": session_id, "query": "Turn 2"})
        self.assertEqual(resp2["result"]["session_id"], session_id)

    async def test_jsonrpc_error_propagation_unauthenticated(self) -> None:
        """Verify unauthenticated requests properly return JSON-RPC error -32000."""
        resp = await self._http_rpc("jarvis.turn.process", {"query": "test without auth"}, auth_token="wrong-token")
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32000)

    async def test_jsonrpc_error_propagation_method_not_found(self) -> None:
        """Verify invalid methods return JSON-RPC error -32601."""
        resp = await self._http_rpc("jarvis.unknown_method", {})
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    async def test_http_dev_bridge_health_endpoint(self) -> None:
        """Verify HTTP /health returns 200 OK with online status."""
        data = await self._http_get("/health")
        self.assertEqual(data["status"], "ONLINE")
        self.assertEqual(data["daemon"], "JARVIS")

    async def test_approval_flow_over_http_bridge(self) -> None:
        """Verify sensitive tool execution triggers confirmation and responds with approval token."""
        self.mock_provider.register_tool_trigger(
            "send critical alert",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "alert-1", "target_email": "security@company.com"},
            ),
        )
        self.mock_provider.register_tool_trigger(
            "execute approved action: mock_email_sender",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "alert-1", "target_email": "security@company.com"},
            ),
        )

        create_resp = await self._http_rpc("jarvis.session.create", {"user_name": "Suprith"})
        session_id = create_resp["result"]["session_id"]

        turn_resp = await self._http_rpc("jarvis.turn.process", {
            "session_id": session_id,
            "query": "Please send critical alert now",
        })
        self.assertEqual(turn_resp["result"]["status"], "AWAITING_CONFIRMATION")
        self.assertTrue(turn_resp["result"]["requires_confirmation"])
        card = turn_resp["result"]["approval_card"]
        self.assertEqual(card["action_name"], "mock_email_sender")

        # Approve action
        approve_resp = await self._http_rpc("jarvis.approval.respond", {
            "card_id": card["card_id"],
            "decision": "APPROVE",
        })
        self.assertEqual(approve_resp["result"]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()

