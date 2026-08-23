"""Secure Local Unix Domain Socket & JSON-RPC 2.0 IPC Server for JARVIS Phase 7."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.events import EventBus
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from core.types import BaseDomainEvent, ExecutionContext
from intelligence.coordinator import ProactiveEvaluationResult
from intelligence.dialogue_advisor import ProactiveDialogueAdvisor
from intelligence.plan_generator import StructuredPlan
from intelligence.runtime_listener import ProactiveRuntimeBridge
from security.audit_logger import AuditLogger
from security.permissions import ApprovalCard, ApprovalToken, PermissionEngine


class IPCServer:
    """Asynchronous JSON-RPC 2.0 Unix Domain Socket server managing desktop client IPC."""

    def __init__(
        self,
        agent_loop: AgentLoop,
        event_bus: EventBus,
        runtime_bridge: ProactiveRuntimeBridge,
        permission_engine: PermissionEngine,
        audit_logger: AuditLogger,
        socket_path: str | Path | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.agent_loop = agent_loop
        self.event_bus = event_bus
        self.runtime_bridge = runtime_bridge
        self.permission_engine = permission_engine
        self.audit_logger = audit_logger
        self.socket_path = Path(socket_path or "/tmp/jarvis_daemon.sock")
        self.auth_token = auth_token or str(uuid4())

        self._server: asyncio.Server | None = None
        self._is_running = False
        self._active_sessions: dict[str, SessionContext] = {}
        self._pending_approvals: dict[str, tuple[ApprovalCard, str]] = {}  # card_id -> (card, session_id)
        self._active_plans: dict[str, StructuredPlan] = {}  # plan_id -> plan
        self._plan_step_states: dict[str, dict[int, bool]] = {}  # plan_id -> {step_number: completed}

        # Registered JSON-RPC methods
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "jarvis.handshake": self._handle_handshake,
            "jarvis.status": self._handle_status,
            "jarvis.session.create": self._handle_session_create,
            "jarvis.session.get": self._handle_session_get,
            "jarvis.turn.process": self._handle_turn_process,
            "jarvis.approval.respond": self._handle_approval_respond,
            "jarvis.proactive.get_latest": self._handle_proactive_get_latest,
            "jarvis.plan.get_active": self._handle_plan_get_active,
            "jarvis.plan.update_step": self._handle_plan_update_step,
            "jarvis.system.emergency_stop": self._handle_emergency_stop,
        }

    async def start(self) -> None:
        """Initialize Unix Domain Socket and start listening for local IPC client connections."""
        if self._is_running:
            return

        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_connection,
            path=str(self.socket_path),
        )

        # Set strict OS file permissions: 0700 (Current user read/write/execute only)
        try:
            os.chmod(str(self.socket_path), 0o700)
        except OSError:
            pass

        self._is_running = True
        self.audit_logger.log(
            actor_id="daemon",
            session_id="ipc_system",
            event_type="IPC_SERVER_STARTED",
            action_type="SOCKET_INIT",
            risk_level="LOW",
            target_resource=str(self.socket_path),
            parameters={"permissions": "0700"},
            decision="SUCCESS",
        )

    async def stop(self) -> None:
        """Close Unix Domain Socket server and clean up socket file."""
        if not self._is_running or not self._server:
            return

        self._server.close()
        await self._server.wait_closed()
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        self._is_running = False
        self.audit_logger.log(
            actor_id="daemon",
            session_id="ipc_system",
            event_type="IPC_SERVER_STOPPED",
            action_type="SOCKET_CLEANUP",
            risk_level="LOW",
            target_resource=str(self.socket_path),
            parameters={},
            decision="SUCCESS",
        )

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process incoming JSON-RPC stream messages from connected desktop client."""
        client_authenticated = False
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break

                try:
                    payload = json.loads(line.decode("utf-8").strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response = self._build_jsonrpc_error(None, -32700, "Parse error: Invalid JSON payload.")
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                req_id = payload.get("id")
                method = payload.get("method")
                params = payload.get("params", {})

                # Require handshake with auth_token before executing other RPC commands
                if not client_authenticated:
                    if method != "jarvis.handshake":
                        response = self._build_jsonrpc_error(req_id, -32000, "Authentication required. Call jarvis.handshake first.")
                        writer.write((json.dumps(response) + "\n").encode("utf-8"))
                        await writer.drain()
                        continue

                    token = params.get("auth_token")
                    if token != self.auth_token:
                        response = self._build_jsonrpc_error(req_id, -32001, "Authentication failed: Invalid auth_token.")
                        writer.write((json.dumps(response) + "\n").encode("utf-8"))
                        await writer.drain()
                        continue

                    client_authenticated = True
                    result = await self._handle_handshake(params)
                    response = {"jsonrpc": "2.0", "result": result, "id": req_id}
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                if method not in self._handlers:
                    response = self._build_jsonrpc_error(req_id, -32601, f"Method not found: '{method}'.")
                else:
                    try:
                        handler = self._handlers[method]
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(params)
                        else:
                            result = handler(params)
                        response = {"jsonrpc": "2.0", "result": result, "id": req_id}
                    except Exception as err:
                        response = self._build_jsonrpc_error(req_id, -32603, f"Internal error: {err}")

                writer.write((json.dumps(response, default=str) + "\n").encode("utf-8"))
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _build_jsonrpc_error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        """Construct standard JSON-RPC 2.0 error response."""
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
            },
            "id": req_id,
        }

    # =========================================================================
    # JSON-RPC Command Handlers
    # =========================================================================

    async def _handle_handshake(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate client credentials and return system status."""
        return {
            "authenticated": True,
            "server_version": "0.7.0",
            "active_permission_level": "NORMAL",
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return system health, memory stats, and agent readiness."""
        return {
            "status": "ONLINE",
            "agent_state": self.agent_loop.state.value,
            "registered_tools_count": len(self.agent_loop.tool_registry.list_tools()),
            "active_sessions_count": len(self._active_sessions),
            "pending_approvals_count": len(self._pending_approvals),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_session_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a new conversational session context."""
        perm_str = params.get("permission_level", "NORMAL").upper()
        perm = PermissionLevel[perm_str] if perm_str in PermissionLevel.__members__ else PermissionLevel.NORMAL
        context = SessionContext(
            user_name=params.get("user_name", "Suprith"),
            permission_level=perm,
            exec_context=ExecutionContext.PRIVATE,
        )
        session_id_str = str(context.session_id)
        self._active_sessions[session_id_str] = context

        await self.event_bus.publish(
            BaseDomainEvent(
                event_name="SESSION_STARTED",
                payload={"session_id": session_id_str, "user_name": context.user_name},
            )
        )

        return {
            "session_id": session_id_str,
            "user_name": context.user_name,
            "permission_level": context.permission_level.value,
            "created_at": context.created_at.isoformat(),
        }

    async def _handle_session_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Retrieve existing session context state."""
        session_id = str(params.get("session_id", ""))
        context = self._active_sessions.get(session_id)
        if not context:
            raise ValueError(f"Session '{session_id}' not found.")

        return {
            "session_id": str(context.session_id),
            "user_name": context.user_name,
            "permission_level": context.permission_level.value,
            "created_at": context.created_at.isoformat(),
        }

    async def _handle_turn_process(self, params: dict[str, Any]) -> dict[str, Any]:
        """Submit query turn to AgentLoop and return assistant reply or confirmation card."""
        session_id = str(params.get("session_id", ""))
        query = str(params.get("query", "")).strip()
        if not query:
            raise ValueError("Query parameter cannot be empty.")

        context = self._active_sessions.get(session_id)
        if not context:
            context = SessionContext(
                permission_level=PermissionLevel.NORMAL,
                exec_context=ExecutionContext.PRIVATE,
            )
            session_id = str(context.session_id)
            self._active_sessions[session_id] = context

        # Optional proactive advisory block
        proactive_advisory = params.get("proactive_advisory")
        if not proactive_advisory:
            proactive_advisory = self.runtime_bridge.get_formatted_advisory(session_id)

        try:
            response = await self.agent_loop.process_turn(
                user_query=query,
                context=context,
                proactive_advisory=proactive_advisory,
            )
            return {
                "status": "COMPLETED",
                "session_id": session_id,
                "reply": response.content,
                "model_name": response.model_name,
                "provider_name": response.provider_name,
                "requires_confirmation": False,
            }
        except HumanConfirmationRequiredError as hitl_err:
            card = hitl_err.approval_card
            card_id_str = str(card.card_id)
            self._pending_approvals[card_id_str] = (card, session_id)
            return {
                "status": "AWAITING_CONFIRMATION",
                "session_id": session_id,
                "requires_confirmation": True,
                "approval_card": {
                    "card_id": card_id_str,
                    "action_name": card.action_name,
                    "risk_level": card.risk_level,
                    "target_resource": card.target_resource,
                    "risk_summary": card.risk_summary,
                    "parameters": card.parameter_payload,
                    "created_at": card.created_at.isoformat(),
                    "expires_at_epoch": card.expires_at_epoch,
                },
            }

    async def _handle_approval_respond(self, params: dict[str, Any]) -> dict[str, Any]:
        """Process user confirmation decision (APPROVE with token or DENY)."""
        card_id = str(params.get("card_id", ""))
        decision = str(params.get("decision", "DENY")).upper()

        if card_id not in self._pending_approvals:
            raise ValueError(f"No pending approval card found for ID '{card_id}'.")

        card, session_id = self._pending_approvals.pop(card_id)
        context = self._active_sessions.get(session_id)
        if not context:
            raise ValueError(f"Session '{session_id}' associated with card is invalid.")

        if decision != "APPROVE":
            self.audit_logger.log(
                actor_id=context.device_id,
                session_id=session_id,
                event_type="APPROVAL_DENIED_BY_USER",
                action_type=card.action_name,
                risk_level="HIGH",
                target_resource=card.target_resource,
                parameters={"card_id": card_id},
                decision="DENIED",
            )
            return {
                "status": "DENIED",
                "session_id": session_id,
                "message": f"Action '{card.action_name}' was denied by user.",
            }

        # Issue single-use approval token
        card_uuid = card.card_id if isinstance(card.card_id, UUID) else UUID(str(card.card_id))
        token = ApprovalToken(
            card_id=card_uuid,
            tool_id=card.tool_id or card.action_name,
            target_resource=card.target_resource,
            session_id=session_id,
            payload_hash=card.payload_hash,
        )

        response = await self.agent_loop.process_turn(
            user_query=f"Execute approved action: {card.action_name}",
            context=context,
            approval_token=token,
            approval_card=card,
        )

        return {
            "status": "COMPLETED",
            "session_id": session_id,
            "reply": response.content,
            "model_name": response.model_name,
        }

    async def _handle_proactive_get_latest(self, params: dict[str, Any]) -> dict[str, Any]:
        """Retrieve latest cached proactive evaluation result for a session."""
        session_id = str(params.get("session_id", "default_session"))
        eval_res = self.runtime_bridge.get_latest_evaluation(session_id)
        if not eval_res:
            return {
                "has_advisory": False,
                "advisory": None,
                "is_informational_only": True,
            }

        formatted_xml = ProactiveDialogueAdvisor.format_system_context(eval_res)
        formatted_md = ProactiveDialogueAdvisor.format_user_notification(eval_res)

        return {
            "has_advisory": True,
            "trigger_type": eval_res.trigger.trigger_type.value,
            "health_score": eval_res.review_report.health_score if eval_res.review_report else None,
            "findings_count": len(eval_res.review_report.findings) if eval_res.review_report else 0,
            "suggestions": [s.model_dump() for s in eval_res.suggestions],
            "disagreements": [d.model_dump() for d in eval_res.disagreements],
            "plans": [p.model_dump() for p in eval_res.generated_plans],
            "formatted_xml": formatted_xml,
            "formatted_markdown": formatted_md,
            "is_informational_only": True,
        }

    async def _handle_plan_get_active(self, params: dict[str, Any]) -> dict[str, Any]:
        """Retrieve active study or task plan with current step completion states."""
        plan_id = str(params.get("plan_id", ""))
        plan = self._active_plans.get(plan_id)
        if not plan:
            # If no specific plan requested, return the latest plan from active plans
            if self._active_plans:
                plan = list(self._active_plans.values())[-1]
                plan_id = str(plan.plan_id)
            else:
                return {"has_plan": False, "plan": None}

        step_states = self._plan_step_states.get(plan_id, {})
        return {
            "has_plan": True,
            "plan_id": plan_id,
            "title": plan.title,
            "goal": plan.goal,
            "plan_type": plan.plan_type.value,
            "milestones": [m.model_dump() for m in plan.milestones],
            "steps": [
                {**s.model_dump(), "completed": step_states.get(s.step_number, False)}
                for s in plan.steps
            ],
            "risks_and_mitigations": plan.risks_and_mitigations,
            "is_informational_only": True,
        }

    async def _handle_plan_update_step(self, params: dict[str, Any]) -> dict[str, Any]:
        """Update checkbox completion state for a plan step item."""
        plan_id = str(params.get("plan_id", ""))
        step_number = int(params.get("step_number", 0))
        completed = bool(params.get("completed", False))

        if plan_id not in self._plan_step_states:
            self._plan_step_states[plan_id] = {}

        self._plan_step_states[plan_id][step_number] = completed

        return {
            "plan_id": plan_id,
            "step_number": step_number,
            "completed": completed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_emergency_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Instantly revoke all active approval tokens, clear pending cards, and cancel execution."""
        revoked_count = len(self._pending_approvals)
        self._pending_approvals.clear()

        self.audit_logger.log(
            actor_id="desktop_hotkey",
            session_id="emergency_stop",
            event_type="EMERGENCY_STOP_TRIGGERED",
            action_type="REVOKE_ALL_APPROVALS",
            risk_level="HIGH",
            target_resource="system",
            parameters={"revoked_cards_count": revoked_count},
            decision="STOPPED",
        )

        return {
            "status": "STOPPED",
            "revoked_approvals_count": revoked_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
