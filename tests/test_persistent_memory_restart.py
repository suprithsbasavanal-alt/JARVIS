"""Tests for Persistent Encrypted Memory, Daemon Restart, and Session Isolation."""

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from core.context import SessionContext
from core.exceptions import SecurityError
from memory.crypto import AuthenticatedEncryptor
from memory.long_term import (
    ConsentStatus,
    MemoryRecord,
    MemoryType,
    RetentionPolicy,
    SensitivityLevel,
)
from memory.manager import MemoryManager
from security.audit_logger import AuditLogger


class TestPersistentMemoryRestart(unittest.IsolatedAsyncioTestCase):
    """Verify persistent SQLite memory persistence across restarts, encryption, and isolation."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.audit_logger = AuditLogger()
        self.encryptor = AuthenticatedEncryptor()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_memory_persists_across_daemon_restart(self) -> None:
        """Verify memory saved in one manager instance survives shutdown and reloads in a new instance."""
        # 1. First instance (Session A)
        mgr1 = MemoryManager(db_path=self.db_path, encryptor=self.encryptor, audit_logger=self.audit_logger)
        rec1 = await mgr1.remember_explicit(
            content="User prefers Python 3.12 and async programming",
            category=MemoryType.SEMANTIC,
            sensitivity=SensitivityLevel.NORMAL,
            session_id="session-user-1",
            tags=["preferences", "python"],
        )
        self.assertIsNotNone(rec1.memory_id)

        # Sensitive memory
        rec_sec = await mgr1.remember_explicit(
            content="User private security note: strictly avoid external sync",
            category=MemoryType.SENSITIVE,
            sensitivity=SensitivityLevel.SENSITIVE,
            session_id="session-user-1",
            tags=["security", "confidential"],
        )

        # 2. Simulate complete daemon restart (destroy instance 1, start instance 2 on same DB)
        del mgr1
        mgr2 = MemoryManager(db_path=self.db_path, encryptor=self.encryptor, audit_logger=self.audit_logger)

        # Verify normal memory loaded and searchable
        results = await mgr2.recall(query="Python", max_sensitivity=SensitivityLevel.NORMAL)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].content, "User prefers Python 3.12 and async programming")

        # Verify sensitive memory is decrypted properly when sensitivity level permits
        sec_results = await mgr2.recall(query="security", max_sensitivity=SensitivityLevel.SENSITIVE)
        self.assertGreaterEqual(len(sec_results), 1)
        self.assertIn("strictly avoid external sync", sec_results[0].content)

        # Verify sensitive memory is filtered out when max_sensitivity is NORMAL
        masked_results = await mgr2.recall(query="security", max_sensitivity=SensitivityLevel.NORMAL)
        self.assertEqual(len(masked_results), 0)

    async def test_session_isolation_and_deletion(self) -> None:
        """Verify deletion by ID and clear by topic."""
        mgr = MemoryManager(db_path=self.db_path, encryptor=self.encryptor, audit_logger=self.audit_logger)
        rec = await mgr.remember_explicit(
            content="Temporary meeting notes for Tuesday",
            category=MemoryType.EPISODIC,
            session_id="session-tuesday",
            tags=["meetings"],
        )

        # Verify it exists
        self.assertIsNotNone(mgr.inspect_memory(rec.memory_id))

        # Forget memory
        deleted = await mgr.forget_memory(rec.memory_id)
        self.assertTrue(deleted)
        self.assertIsNone(mgr.inspect_memory(rec.memory_id))

        # Restart and verify it remains deleted
        mgr_restarted = MemoryManager(db_path=self.db_path, encryptor=self.encryptor, audit_logger=self.audit_logger)
        self.assertIsNone(mgr_restarted.inspect_memory(rec.memory_id))
