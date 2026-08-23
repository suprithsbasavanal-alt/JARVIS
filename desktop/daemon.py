"""Desktop Core Daemon Service Runner for JARVIS Phase 7."""

import asyncio
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
        self.model_router.register_provider(self.mock_provider)

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

        # 8. IPC Server
        self.ipc_server = IPCServer(
            agent_loop=self.agent_loop,
            event_bus=self.event_bus,
            runtime_bridge=self.runtime_bridge,
            permission_engine=self.permission_engine,
            audit_logger=self.audit_logger,
            socket_path=self.socket_path,
            auth_token=self.auth_token,
        )

    def _register_default_tools(self) -> None:
        """Register default sandboxed desktop tools."""
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.tool_registry.register_tool(MockEmailSenderTool(mock_fs=self.mock_fs))

    async def run(self) -> None:
        """Run the daemon service until terminated."""
        await self.ipc_server.start()

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
