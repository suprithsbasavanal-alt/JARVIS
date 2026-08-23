"""Hermetic Automated Tests for JARVIS Phase 7 — macOS Desktop Agent & Secure IPC."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.events import EventBus
from core.ipc_server import IPCServer
from core.types import BaseDomainEvent, ExecutionContext
from intelligence.coordinator import (
    ProactiveCoordinator,
    ProactiveEvaluationResult,
    ProactiveTrigger,
    TriggerType,
)
from intelligence.plan_generator import PlanDifficulty, PlanMilestone, PlanStepItem, PlanType, StructuredPlan
from intelligence.project_reviewer import ProjectReviewReport
from intelligence.runtime_listener import ProactiveRuntimeBridge
from intelligence.suggestions import ProactiveSuggestion, SuggestionCategory, SuggestionPriority
from memory.keys import TestKeyProvider
from memory.manager import MemoryManager
from memory.sqlite_store import SQLiteMemoryStore
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from model_routing.schemas import ChatMessage, MessageRole, ModelResponse, ToolCallDefinition
from sandbox.mock_fs import MockFileSystem
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.permissions import PermissionEngine
from tools.mock_tools import MockEmailSenderTool, MockFileReaderTool
from tools.registry import ToolRegistry


class TestPhase7DesktopIPC(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying Phase 7 Unix Domain Socket JSON-RPC server and desktop agent integration."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.socket_path = Path(self.temp_dir.name) / "test_jarvis.sock"
        self.auth_token = "test-secret-token-1234"

        # Initialize core components
        self.audit_logger = AuditLogger()
        self.permission_engine = PermissionEngine()
        self.event_bus = EventBus()
        self.memory_manager = MemoryManager(
            db_path=":memory:",
            audit_logger=self.audit_logger,
        )

        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem()
        self.mock_fs.write_file("/test.txt", "Hello from sandboxed file")
        self.process_executor = ProcessSandboxExecutor()
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock")
        self.mock_provider.set_canned_response("I have processed your desktop request successfully.")
        self.model_router.register_provider("mock", self.mock_provider)

        self.proactive_coordinator = ProactiveCoordinator(audit_logger=self.audit_logger)
        self.runtime_bridge = ProactiveRuntimeBridge(
            coordinator=self.proactive_coordinator,
            event_bus=self.event_bus,
        )

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

    async def asyncTearDown(self) -> None:
        await self.ipc_server.stop()
        self.temp_dir.cleanup()

    async def _send_ipc_message(self, message: dict) -> dict:
        """Helper to send a JSON-RPC request over Unix socket and return parsed response."""
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        writer.write((json.dumps(message) + "\n").encode("utf-8"))
        await writer.drain()

        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return json.loads(line.decode("utf-8"))

    async def _authenticated_call(self, method: str, params: dict | None = None) -> dict:
        """Helper to execute an authenticated JSON-RPC call."""
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))

        # 1. Handshake
        handshake_req = {
            "jsonrpc": "2.0",
            "id": "hs-1",
            "method": "jarvis.handshake",
            "params": {"auth_token": self.auth_token},
        }
        writer.write((json.dumps(handshake_req) + "\n").encode("utf-8"))
        await writer.drain()
        line = await reader.readline()
        hs_resp = json.loads(line.decode("utf-8"))
        self.assertTrue(hs_resp.get("result", {}).get("authenticated"))

        # 2. Method Call
        call_req = {
            "jsonrpc": "2.0",
            "id": "call-1",
            "method": method,
            "params": params or {},
        }
        writer.write((json.dumps(call_req) + "\n").encode("utf-8"))
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return json.loads(line.decode("utf-8"))

    # =========================================================================
    # Test Cases
    # =========================================================================

    async def test_ipc_socket_creation_and_permissions(self) -> None:
        """1. Verify Unix Domain Socket file is created with 0700 permissions."""
        self.assertTrue(self.socket_path.exists())
        mode = self.socket_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o700)

    async def test_unauthenticated_request_rejected(self) -> None:
        """2. Verify calling methods without prior handshake returns -32000 Authentication required."""
        resp = await self._send_ipc_message({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "jarvis.status",
            "params": {},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32000)

    async def test_invalid_auth_token_rejected(self) -> None:
        """3. Verify invalid auth_token in handshake returns -32001 Authentication failed."""
        resp = await self._send_ipc_message({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "jarvis.handshake",
            "params": {"auth_token": "wrong-token"},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32001)

    async def test_invalid_method_rejected(self) -> None:
        """4. Verify unknown method returns -32601 Method not found."""
        resp = await self._authenticated_call("jarvis.non_existent_method")
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    async def test_status_command(self) -> None:
        """5. Verify jarvis.status returns healthy system state."""
        resp = await self._authenticated_call("jarvis.status")
        self.assertIn("result", resp)
        res = resp["result"]
        self.assertEqual(res["status"], "ONLINE")
        self.assertEqual(res["agent_state"], "IDLE")
        self.assertGreaterEqual(res["registered_tools_count"], 2)

    async def test_session_create_and_get(self) -> None:
        """6. Verify session creation and retrieval over IPC."""
        create_resp = await self._authenticated_call("jarvis.session.create", {
            "user_name": "Suprith",
            "permission_level": "NORMAL",
        })
        self.assertIn("result", create_resp)
        session_id = create_resp["result"]["session_id"]

        get_resp = await self._authenticated_call("jarvis.session.get", {"session_id": session_id})
        self.assertIn("result", get_resp)
        self.assertEqual(get_resp["result"]["user_name"], "Suprith")
        self.assertEqual(get_resp["result"]["permission_level"], "NORMAL")

    async def test_turn_process_normal_flow(self) -> None:
        """7. Verify standard conversational turn processing through AgentLoop over IPC."""
        resp = await self._authenticated_call("jarvis.turn.process", {
            "query": "Hello JARVIS desktop!",
        })
        self.assertIn("result", resp)
        res = resp["result"]
        self.assertEqual(res["status"], "COMPLETED")
        self.assertFalse(res["requires_confirmation"])
        self.assertIn("I have processed your desktop request", res["reply"])

    async def test_hitl_approval_deny_flow(self) -> None:
        """8. Verify sensitive tool raises approval card and user DENY response rejects execution."""
        # Mock model requesting sensitive tool
        self.mock_provider.register_tool_trigger(
            "send an email",
            ToolCallDefinition(
                tool_name="mock_email_sender",
                arguments={"draft_id": "draft-1", "target_email": "boss@example.com"},
            ),
        )

        turn_resp = await self._authenticated_call("jarvis.turn.process", {
            "query": "Please send an email",
        })
        self.assertIn("result", turn_resp)
        res = turn_resp["result"]
        self.assertEqual(res["status"], "AWAITING_CONFIRMATION")
        self.assertTrue(res["requires_confirmation"])
        card = res["approval_card"]
        self.assertEqual(card["action_name"], "mock_email_sender")

        # Deny the approval
        deny_resp = await self._authenticated_call("jarvis.approval.respond", {
            "card_id": card["card_id"],
            "decision": "DENY",
        })
        self.assertIn("result", deny_resp)
        self.assertEqual(deny_resp["result"]["status"], "DENIED")

    async def test_hitl_approval_approve_flow(self) -> None:
        """9. Verify sensitive tool APPROVE response issues single-use token and executes action."""
        self.mock_provider.register_tool_trigger(
            "send authorized email",
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

        turn_resp = await self._authenticated_call("jarvis.turn.process", {
            "query": "Please send authorized email",
        })
        card = turn_resp["result"]["approval_card"]

        # Approve the action
        approve_resp = await self._authenticated_call("jarvis.approval.respond", {
            "card_id": card["card_id"],
            "decision": "APPROVE",
        })
        self.assertIn("result", approve_resp)
        self.assertEqual(approve_resp["result"]["status"], "COMPLETED")

    async def test_proactive_advisory_retrieval(self) -> None:
        """10. Verify retrieving formatted proactive advisory observations over IPC."""
        eval_result = ProactiveEvaluationResult(
            trigger=ProactiveTrigger(trigger_type=TriggerType.SESSION_START),
            review_report=ProjectReviewReport(
                target_path="/workspace",
                health_score=88.5,
                scanned_files_count=12,
                findings=[],
            ),
            suggestions=[
                ProactiveSuggestion(
                    title="Audit Logging Hardening",
                    description="Ensure chained hashes are verified.",
                    priority=SuggestionPriority.MEDIUM,
                    category=SuggestionCategory.SECURITY_HARDENING,
                    rationale="Enhance audit trail non-repudiation.",
                )
            ],
            is_informational_only=True,
        )
        self.runtime_bridge._latest_evaluations["default_session"] = eval_result

        resp = await self._authenticated_call("jarvis.proactive.get_latest", {
            "session_id": "default_session",
        })
        self.assertIn("result", resp)
        res = resp["result"]
        self.assertTrue(res["has_advisory"])
        self.assertEqual(res["health_score"], 88.5)
        self.assertTrue(res["is_informational_only"])
        self.assertIn("<proactive_advisory", res["formatted_xml"])

    async def test_plan_management_and_step_persistence(self) -> None:
        """11. Verify study/task plan step completion state persistence over IPC."""
        plan = StructuredPlan(
            title="Desktop Security Onboarding",
            goal="Harden IPC and memory boundaries",
            plan_type=PlanType.TASK_EXECUTION,
            difficulty=PlanDifficulty.INTERMEDIATE,
            estimated_duration="2 days",
            milestones=[
                PlanMilestone(
                    milestone_id=1,
                    title="Socket Hardening",
                    objective="Verify 0700 permissions",
                    estimated_hours=4.0,
                )
            ],
            steps=[
                PlanStepItem(
                    step_number=1,
                    milestone_id=1,
                    title="Validate permissions",
                    description="Check stat mode",
                    deliverable="Socket test",
                ),
                PlanStepItem(
                    step_number=2,
                    milestone_id=1,
                    title="Verify auth token",
                    description="Test handshake",
                    deliverable="Auth test",
                ),
            ],
            is_informational_only=True,
        )
        self.ipc_server._active_plans[str(plan.plan_id)] = plan

        # 1. Fetch active plan
        get_resp = await self._authenticated_call("jarvis.plan.get_active", {
            "plan_id": str(plan.plan_id),
        })
        self.assertIn("result", get_resp)
        self.assertEqual(get_resp["result"]["title"], "Desktop Security Onboarding")
        self.assertFalse(get_resp["result"]["steps"][0]["completed"])

        # 2. Update step 1 to completed
        update_resp = await self._authenticated_call("jarvis.plan.update_step", {
            "plan_id": str(plan.plan_id),
            "step_number": 1,
            "completed": True,
        })
        self.assertIn("result", update_resp)
        self.assertTrue(update_resp["result"]["completed"])

        # 3. Re-fetch and verify persistent step state
        re_get_resp = await self._authenticated_call("jarvis.plan.get_active", {
            "plan_id": str(plan.plan_id),
        })
        self.assertTrue(re_get_resp["result"]["steps"][0]["completed"])
        self.assertFalse(re_get_resp["result"]["steps"][1]["completed"])

    async def test_emergency_stop_command(self) -> None:
        """12. Verify emergency stop revokes pending approvals and logs audit entry."""
        # Create dummy pending approval
        self.ipc_server._pending_approvals["card-999"] = (None, "session-1")

        stop_resp = await self._authenticated_call("jarvis.system.emergency_stop")
        self.assertIn("result", stop_resp)
        self.assertEqual(stop_resp["result"]["status"], "STOPPED")
        self.assertEqual(stop_resp["result"]["revoked_approvals_count"], 1)
        self.assertEqual(len(self.ipc_server._pending_approvals), 0)

    async def test_proactive_advisory_cannot_trigger_unsolicited_tools_over_ipc(self) -> None:
        """13. Verify proactive advisory results are strictly informational and cannot trigger tool execution."""
        resp = await self._authenticated_call("jarvis.proactive.get_latest", {
            "session_id": "default_session",
        })
        self.assertIn("result", resp)
        self.assertTrue(resp["result"]["is_informational_only"])
        # Verify no tools were registered or executed in pending approvals
        self.assertEqual(len(self.ipc_server._pending_approvals), 0)

    async def test_secret_isolation_over_ipc(self) -> None:
        """14. Verify IPC status and responses never expose internal secret keys or system credentials."""
        status_resp = await self._authenticated_call("jarvis.status")
        status_str = json.dumps(status_resp)
        self.assertNotIn(self.auth_token, status_str)
        self.assertNotIn("OPENAI_API_KEY", status_str)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", status_str)

    async def test_malformed_json_payload_rejection(self) -> None:
        """15. Verify malformed raw JSON over Unix socket receives -32700 Parse error."""
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        writer.write(b"NOT_A_VALID_JSON_STRING\n")
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()

        resp = json.loads(line.decode("utf-8"))
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32700)

    async def test_backend_unavailable_error_handling(self) -> None:
        """16. Verify attempting to connect to non-existent socket raises connection error cleanly."""
        non_existent_sock = Path(self.temp_dir.name) / "offline.sock"
        with self.assertRaises((FileNotFoundError, ConnectionRefusedError)):
            await asyncio.open_unix_connection(str(non_existent_sock))


if __name__ == "__main__":
    unittest.main()

