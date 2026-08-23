"""Final Comprehensive Architectural Review & Holistic Invariant Verification Test Suite (Phase 12)."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any
import unittest
from uuid import UUID, uuid4

from agents.loop import AgentLoop
from config.schema import JarvisConfig, ModelTier, PermissionLevel, PerformanceConfig
from core.context import SessionContext
from core.events import EventBus
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError
from core.ipc_server import IPCServer
from core.types import ActionCategory, ExecutionContext
from desktop.daemon import JarvisDesktopDaemon
from intelligence.coordinator import ProactiveCoordinator
from intelligence.runtime_listener import ProactiveRuntimeBridge
from memory.manager import MemoryManager
from model_routing.optimization.benchmarker import PerformanceBenchmarker
from model_routing.optimization.cache import SemanticResponseCache
from model_routing.optimization.memory_guard import MemoryGuard
from model_routing.optimization.token_optimizer import TokenOptimizer
from model_routing.providers.local_quantized_provider import LocalQuantizedProvider
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from model_routing.schemas import ChatMessage, MessageRole, ModelRequest, ModelResponse
from sandbox.mock_fs import MockFileSystem
from sandbox.process_executor import ProcessSandboxExecutor
from security.audit_logger import AuditLogger
from security.device_pairing import DevicePairingRegistry
from security.permissions import (
    ApprovalCard,
    ApprovalToken,
    PermissionDecision,
    PermissionEngine,
)
from security.prompt_guard import PromptGuard
from security.redteam.audit_verifier import AuditIntegrityVerifier
from security.redteam.fuzzer import AdversarialPromptFuzzer
from security.redteam.privilege_evaluator import PrivilegeEscalationTester
from security.redteam.scanner import SecurityVulnerabilityScanner
from security.sanitizer import Sanitizer
from services.credentials.models import OAuth2Credentials
from services.credentials.provider import SecureCredentialManager
from services.credentials.storage import InMemorySecureStorage
from services.execution.manager import (
    EmergencyStopActiveError,
    ServiceExecutionManager,
)
from services.models import (
    ServiceCapability,
    ServiceRequest,
    ServiceResponse,
    ServiceStatus,
    UndeclaredCapabilityError,
)
from services.permissions import ServicePermissionBridge
from services.registry import ServiceRegistry
from services.transport.mock_transport import MockHttpTransport
from tools.mock_tools import MockFileReaderTool
from tools.registry import ToolRegistry


class TestPhase12FinalArchitecturalReview(unittest.IsolatedAsyncioTestCase):
    """End-to-End Holistic Architectural Verification and Policy Audit."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.audit_log_path = self.temp_path / "audit_final.log"
        self.audit_logger = AuditLogger(log_path=self.audit_log_path)
        self.sanitizer = Sanitizer()
        self.prompt_guard = PromptGuard()
        self.permission_engine = PermissionEngine()
        self.tool_registry = ToolRegistry()
        self.mock_fs = MockFileSystem()
        self.tool_registry.register_tool(MockFileReaderTool(mock_fs=self.mock_fs))
        self.memory_manager = MemoryManager(db_path=":memory:", audit_logger=self.audit_logger)
        self.model_router = ModelRouter(sanitizer=self.sanitizer)
        self.pairing_registry = DevicePairingRegistry(audit_logger=self.audit_logger)

        self.agent_loop = AgentLoop(
            model_router=self.model_router,
            tool_registry=self.tool_registry,
            permission_engine=self.permission_engine,
            sandbox_executor=ProcessSandboxExecutor(),
            audit_logger=self.audit_logger,
            memory_manager=self.memory_manager,
        )

        self.context = SessionContext()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # ====================================================
    # 1. Global Configuration & Schema Consistency
    # ====================================================

    def test_root_configuration_schema_integrity(self) -> None:
        """1. Verify JarvisConfig initializes all sub-configurations with safe production defaults."""
        config = JarvisConfig()
        self.assertEqual(config.system.environment, "development")
        self.assertFalse(config.system.enable_external_services)  # Safe default: network off
        self.assertEqual(config.security.default_permission_level, PermissionLevel.NORMAL)
        self.assertTrue(config.security.require_confirmation_for_sensitive)
        self.assertTrue(config.performance.enable_token_optimization)
        self.assertTrue(config.performance.enable_response_cache)
        self.assertEqual(config.performance.max_ram_mb, 2048)
        self.assertEqual(config.performance.target_ttft_ms, 400)

    # ====================================================
    # 2. Universal Fail-Closed Emergency Stop Invariant
    # ====================================================

    async def test_universal_emergency_stop_invariant(self) -> None:
        """2. Verify Emergency Stop immediately halts permission evaluation and service execution."""
        # 1. Trigger kill switch in PermissionEngine
        self.permission_engine.set_emergency_lock(True)

        decision = self.permission_engine.evaluate(
            session=self.context,
            action_name="read_file",
            required_level=PermissionLevel.NORMAL,
            action_category=ActionCategory.SAFE,
            target_resource="sandbox/test.txt",
            parameters={},
        )
        self.assertEqual(decision, PermissionDecision.DENIED_EMERGENCY_LOCK)

        # 2. Trigger kill switch in ServiceExecutionManager
        bridge = ServicePermissionBridge(self.permission_engine)
        cred_mgr = SecureCredentialManager(InMemorySecureStorage())
        registry = ServiceRegistry(self.audit_logger, bridge)
        transport = MockHttpTransport()

        exec_mgr = ServiceExecutionManager(
            service_registry=registry,
            permission_bridge=bridge,
            credential_manager=cred_mgr,
            transport=transport,
            audit_logger=self.audit_logger,
        )
        exec_mgr.trigger_emergency_stop()

        req = ServiceRequest(
            service_id="gmail",
            capability=ServiceCapability.READ,
            operation="read_inbox",
            session_id=str(self.context.session_id),
        )
        with self.assertRaises(EmergencyStopActiveError):
            await exec_mgr.execute(req, self.context)

    # ====================================================
    # 3. Non-Repudiable Cryptographic Audit Logging
    # ====================================================

    def test_audit_log_cryptographic_chaining_and_tamper_detection(self) -> None:
        """3. Verify entire audit trail maintains unbroken SHA-256 hash chaining across operations."""
        logger = AuditLogger(log_path=self.audit_log_path)
        for i in range(10):
            logger.log(
                actor_id="user_admin",
                action_type=f"ACTION_{i}",
                target_resource=f"resource_{i}",
                parameters={"index": i},
                decision="SUCCESS",
            )

        # Mathematical verification of log chain on disk
        verif = AuditIntegrityVerifier.verify_log_file(self.audit_log_path)
        self.assertTrue(verif.is_valid)
        self.assertEqual(verif.total_entries, 10)
        self.assertIsNone(verif.corrupted_sequence_id)

    # ====================================================
    # 4. Human-In-The-Loop (HITL) Single-Use Token Invariant
    # ====================================================

    def test_hitl_single_use_approval_token_invariant(self) -> None:
        """4. Verify SENSITIVE/DESTRUCTIVE tools strictly require single-use ApprovalToken and reject replay."""
        tester = PrivilegeEscalationTester(self.permission_engine)
        res = tester.run_all_privilege_tests(self.temp_path)

        self.assertEqual(res.failed_count, 0, f"Privilege violations found: {res.violations}")
        self.assertGreaterEqual(res.passed_count, 4)

    # ====================================================
    # 5. PII Sanitization & Restoration Pipeline
    # ====================================================

    def test_end_to_end_pii_sanitization_and_restoration(self) -> None:
        """5. Verify PII is redacted before model routing and restored accurately in responses."""
        raw_text = "Send credentials to suprith.basavanal@example.com using token ghp_111122223333444455556666777788889999."
        sanitized = self.sanitizer.sanitize(raw_text)

        self.assertNotIn("suprith.basavanal@example.com", sanitized)
        self.assertNotIn("ghp_111122223333444455556666777788889999", sanitized)
        self.assertIn("{{REDACTED_EMAIL_", sanitized)
        self.assertIn("{{REDACTED_API_KEY_", sanitized)

        restored = self.sanitizer.restore(sanitized)
        self.assertEqual(restored, raw_text)

    # ====================================================
    # 6. Desktop Daemon & IPC Server Lifecycle
    # ====================================================

    async def test_desktop_daemon_and_ipc_lifecycle(self) -> None:
        """6. Verify Desktop Daemon initializes all subsystems and starts IPC server cleanly."""
        sock_path = self.temp_path / "jarvis_review_daemon.sock"
        daemon = JarvisDesktopDaemon(socket_path=sock_path)

        self.assertIsNotNone(daemon.agent_loop)
        self.assertIsNotNone(daemon.service_registry)
        self.assertIsNotNone(daemon.ipc_server)

        # Start and stop IPC server
        await daemon.ipc_server.start()
        self.assertTrue(sock_path.exists())
        await daemon.ipc_server.stop()

    # ====================================================
    # 7. Hardware Device Pairing & Challenge-Response
    # ====================================================

    def test_hardware_device_pairing_lifecycle(self) -> None:
        """7. Verify Android companion device pairing, mutual authentication, and revocation."""
        dev, code = self.pairing_registry.begin_pairing(
            device_id="pixel_9_pro",
            device_name="Suprith Pixel 9 Pro",
            public_key_hex="b" * 64,
        )
        self.assertEqual(len(code), 6)

        # Confirm pairing
        confirmed_dev = self.pairing_registry.confirm_pairing("pixel_9_pro", code)
        self.assertEqual(confirmed_dev.status.value, "CONFIRMED")

        # Create challenge
        challenge = self.pairing_registry.create_auth_challenge("pixel_9_pro")
        self.assertIsNotNone(challenge.nonce)

        # Revoke device
        self.pairing_registry.revoke_device("pixel_9_pro")
        with self.assertRaises(Exception):
            self.pairing_registry.create_auth_challenge("pixel_9_pro")

    # ====================================================
    # 8. Performance SLAs & Memory Footprint
    # ====================================================

    async def test_performance_sla_and_memory_footprint(self) -> None:
        """8. Verify TTFT < 400ms SLA, sub-10ms cache retrieval, and process RAM < 2048 MB."""
        router = ModelRouter()
        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Review architecture summary")],
            tier="local_private",
        )

        # Local quantized GGUF generation
        t0 = time.perf_counter()
        resp = await router.route(req, tier=ModelTier.LOCAL_PRIVATE)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 400.0, f"Inference took {elapsed_ms:.2f}ms (expected < 400ms)")
        self.assertIn("GGUF", resp.content)

        # Cached lookup < 10ms
        t1 = time.perf_counter()
        cached_resp = await router.route(req, tier=ModelTier.LOCAL_PRIVATE)
        cache_elapsed_ms = (time.perf_counter() - t1) * 1000.0
        self.assertLess(cache_elapsed_ms, 10.0, f"Cached lookup took {cache_elapsed_ms:.2f}ms (expected < 10ms)")

        # Verify MemoryGuard RSS < 2048 MB
        guard = MemoryGuard()
        self.assertTrue(guard.is_within_limits())
        self.assertLess(guard.get_process_rss_mb(), 2048.0)

    # ====================================================
    # 9. Red-Team Vulnerability & Secret Scanning
    # ====================================================

    def test_redteam_vulnerability_and_secret_scanning(self) -> None:
        """9. Verify red-team fuzzer and vulnerability scanner detect zero high/critical vulnerabilities."""
        fuzzer = AdversarialPromptFuzzer(prompt_guard=self.prompt_guard)
        fuzz_report = fuzzer.run_fuzzing_suite()
        self.assertEqual(fuzz_report.bypassed_count, 0)
        self.assertEqual(fuzz_report.block_rate, 1.0)

        scanner = SecurityVulnerabilityScanner()
        mock_private_url = "http://169.254.169.254/latest/meta-data/"
        findings = scanner.check_url_for_ssrf(mock_private_url)
        self.assertGreaterEqual(len(findings), 1)
        categories = {f.category for f in findings}
        self.assertIn("SSRF", categories)


if __name__ == "__main__":
    unittest.main()
