"""Shared Pytest Fixtures for Hermetic Testing."""

from pathlib import Path
import pytest
from agents.loop import AgentLoop
from config.schema import PermissionLevel
from core.context import SessionContext
from core.types import ExecutionContext
from memory.manager import MemoryManager
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from sandbox.environment import SandboxEnvironment
from security.audit_logger import AuditLogger
from security.authenticator import Authenticator
from security.permissions import PermissionEngine
from security.prompt_guard import PromptGuard
from security.sanitizer import Sanitizer
from tools.registry import ToolRegistry


@pytest.fixture
def session_context() -> SessionContext:
    """Create standard private session context for Suprith."""
    return SessionContext(
        device_id="test-device-001",
        user_name="Suprith",
        formal_salutation="Sir",
        permission_level=PermissionLevel.NORMAL,
        exec_context=ExecutionContext.PRIVATE,
        active_whitelist_paths=["sandbox/fixtures/mock_files"],
    )


@pytest.fixture
def prompt_guard() -> PromptGuard:
    """Create prompt guard fixture."""
    return PromptGuard()


@pytest.fixture
def sanitizer() -> Sanitizer:
    """Create PII sanitizer fixture."""
    return Sanitizer()


@pytest.fixture
def audit_logger(tmp_path: Path) -> AuditLogger:
    """Create audit logger writing to temporary test directory."""
    return AuditLogger(log_path=tmp_path / "test_audit.log")


@pytest.fixture
def permission_engine() -> PermissionEngine:
    """Create permission engine fixture."""
    return PermissionEngine()


@pytest.fixture
def authenticator() -> Authenticator:
    """Create authenticator fixture."""
    return Authenticator(token_ttl_minutes=15)


@pytest.fixture
def model_router(sanitizer: Sanitizer) -> ModelRouter:
    """Create model router with mock provider."""
    router = ModelRouter(sanitizer=sanitizer)
    router.register_provider("mock", MockModelProvider("mock"))
    return router


@pytest.fixture
def memory_manager() -> MemoryManager:
    """Create memory manager with in-memory mock store."""
    return MemoryManager()


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create empty tool registry."""
    return ToolRegistry()


@pytest.fixture
def sandbox_env() -> SandboxEnvironment:
    """Create hermetic sandbox environment fixture."""
    return SandboxEnvironment()


@pytest.fixture
def agent_loop(
    model_router: ModelRouter,
    permission_engine: PermissionEngine,
    tool_registry: ToolRegistry,
    memory_manager: MemoryManager,
    audit_logger: AuditLogger,
) -> AgentLoop:
    """Create fully wired AgentLoop with mock backends."""
    return AgentLoop(
        model_router=model_router,
        permission_engine=permission_engine,
        tool_registry=tool_registry,
        memory_manager=memory_manager,
        audit_logger=audit_logger,
    )
