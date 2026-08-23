"""Desktop Core Daemon Service Runner for JARVIS Phase 7."""

import asyncio
import json
import os
from pathlib import Path
import signal
import sys
from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.events import EventBus
from core.ipc_server import IPCServer
from intelligence.coordinator import ProactiveCoordinator
from intelligence.runtime_listener import ProactiveRuntimeBridge
from memory.keys import TestKeyProvider
from memory.manager import MemoryManager
from memory.sqlite_store import SQLiteMemoryStore
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from sandbox.mock_fs import MockFileSystem
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.permissions import PermissionEngine
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from tools.mock_tools import MockEmailSenderTool, MockFileReaderTool
from tools.registry import ToolRegistry


class JarvisDesktopDaemon:
    """Manages full lifecycle of JARVIS Desktop Core background daemon."""

    def __init__(self, socket_path: str | Path | None = None, auth_token: str | None = None) -> None:
        self.socket_path = Path(socket_path or "/tmp/jarvis_daemon.sock")
        self.auth_token = auth_token or os.getenv("JARVIS_IPC_TOKEN", "jarvis-desktop-local-token")

        # 1. Core Security & Audit
        self.audit_logger = AuditLogger()
        self.permission_engine = PermissionEngine()

        # 2. Event Bus
        self.event_bus = EventBus()

        # 3. Encrypted Memory Subsystem
        self.memory_manager = MemoryManager(
            db_path=":memory:",
            audit_logger=self.audit_logger,
        )

        # 4. Tool Registry & Sandbox
        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem()
        self.process_executor = ProcessSandboxExecutor()
        self._register_default_tools()

        # 5. Model Routing
        self.model_router = ModelRouter()
        self.mock_provider = MockModelProvider("mock-primary")
        self.model_router.register_provider("mock-primary", self.mock_provider)

        # 6. Proactive Intelligence & Runtime Bridge
        self.proactive_coordinator = ProactiveCoordinator(
            audit_logger=self.audit_logger,
        )
        self.runtime_bridge = ProactiveRuntimeBridge(
            coordinator=self.proactive_coordinator,
            event_bus=self.event_bus,
        )

        # 7. Safe 11-Step AgentLoop
        self.agent_loop = AgentLoop(
            model_router=self.model_router,
            tool_registry=self.tool_registry,
            permission_engine=self.permission_engine,
            sandbox_executor=self.process_executor,
            audit_logger=self.audit_logger,
            memory_manager=self.memory_manager,
        )

        # 8. Service Registry & Permissions Bridge
        self.service_permission_bridge = ServicePermissionBridge(self.permission_engine)
        self.service_registry = ServiceRegistry(
            audit_logger=self.audit_logger,
            permission_bridge=self.service_permission_bridge,
        )

        # 9. IPC Server
        self.ipc_server = IPCServer(
            agent_loop=self.agent_loop,
            event_bus=self.event_bus,
            runtime_bridge=self.runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            socket_path=self.socket_path,
            auth_token=self.auth_token,
            service_registry=self.service_registry,
        )

        # 10. HTTP Dev Bridge (for browser dev preview mode)
        self.http_host = "127.0.0.1"
        self.http_port = int(os.getenv("JARVIS_DEV_HTTP_PORT", "8765"))
        self._http_server: asyncio.Server | None = None

    def _register_default_tools(self) -> None:
        """Register default sandboxed desktop tools."""
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

    async def _handle_http_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle HTTP JSON-RPC 2.0 requests for browser development diagnostic mode."""
        try:
            req_line = await reader.readline()
            if not req_line:
                return
            line_str = req_line.decode("utf-8", errors="ignore").strip()
            parts = line_str.split()
            if len(parts) < 2:
                return
            http_method, path = parts[0].upper(), parts[1]

            headers: dict[str, str] = {}
            while True:
                header_line = await reader.readline()
                if not header_line or header_line == b"\r\n" or header_line == b"\n":
                    break
                h_str = header_line.decode("utf-8", errors="ignore").strip()
                if ":" in h_str:
                    k, v = h_str.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            cors_headers = (
                "Access-Control-Allow-Origin: *\r\n"
                "Access-Control-Allow-Methods: POST, OPTIONS, GET\r\n"
                "Access-Control-Allow-Headers: Content-Type, Authorization, X-Jarvis-Auth-Token\r\n"
                "Connection: close\r\n"
            )

            if http_method == "OPTIONS":
                resp_bytes = (
                    f"HTTP/1.1 204 No Content\r\n{cors_headers}Content-Length: 0\r\n\r\n"
                ).encode("utf-8")
                writer.write(resp_bytes)
                await writer.drain()
                return

            if http_method == "GET" and path == "/health":
                status_dict = {"status": "ONLINE", "version": "0.7.0", "daemon": "JARVIS"}
                resp_body = json.dumps(status_dict)
                resp_bytes = (
                    f"HTTP/1.1 200 OK\r\n{cors_headers}Content-Type: application/json\r\nContent-Length: {len(resp_body.encode('utf-8'))}\r\n\r\n{resp_body}"
                ).encode("utf-8")
                writer.write(resp_bytes)
                await writer.drain()
                return

            if http_method == "POST" and path in ("/", "/rpc"):
                content_len = int(headers.get("content-length", "0"))
                body_bytes = await reader.readexactly(content_len) if content_len > 0 else b""
                try:
                    payload = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    err_body = json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error: Invalid JSON"}, "id": None})
                    resp = (f"HTTP/1.1 400 Bad Request\r\n{cors_headers}Content-Type: application/json\r\nContent-Length: {len(err_body.encode('utf-8'))}\r\n\r\n{err_body}").encode("utf-8")
                    writer.write(resp)
                    await writer.drain()
                    return

                auth_header = headers.get("x-jarvis-auth-token") or headers.get("authorization", "").replace("Bearer ", "")
                req_params = payload.get("params", {}) if isinstance(payload, dict) else {}
                is_authed = (auth_header == self.auth_token) or (isinstance(req_params, dict) and req_params.get("auth_token") == self.auth_token)

                resp_dict, _ = await self.ipc_server.dispatch_rpc_payload(payload, is_authenticated=is_authed)
                resp_body = json.dumps(resp_dict, default=str)
                resp_bytes = (
                    f"HTTP/1.1 200 OK\r\n{cors_headers}Content-Type: application/json\r\nContent-Length: {len(resp_body.encode('utf-8'))}\r\n\r\n{resp_body}"
                ).encode("utf-8")
                writer.write(resp_bytes)
                await writer.drain()
                return

            not_found = json.dumps({"error": "Not Found"})
            resp_bytes = f"HTTP/1.1 404 Not Found\r\n{cors_headers}Content-Length: {len(not_found)}\r\n\r\n{not_found}".encode("utf-8")
            writer.write(resp_bytes)
            await writer.drain()
        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run(self) -> None:
        """Run the daemon service until terminated."""
        await self.ipc_server.start()

        # Start HTTP Dev Bridge for browser dev mode
        try:
            self._http_server = await asyncio.start_server(
                self._handle_http_client,
                host=self.http_host,
                port=self.http_port,
            )
        except Exception as e:
            self.audit_logger.log(
                actor_id="daemon",
                session_id="ipc_system",
                event_type="HTTP_DEV_BRIDGE_FAILED",
                action_type="SERVER_INIT",
                risk_level="LOW",
                target_resource=f"http://{self.http_host}:{self.http_port}",
                parameters={"error": str(e)},
                decision="SKIPPED",
            )

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

        try:
            await stop_event.wait()
        finally:
            if self._http_server:
                self._http_server.close()
                await self._http_server.wait_closed()
            await self.ipc_server.stop()


def main() -> None:
    """CLI entrypoint for JARVIS desktop daemon."""
    daemon = JarvisDesktopDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
