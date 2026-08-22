"""Unified Memory Subsystem Manager for Phase 2.

Coordinates Ephemeral Working Memory, Encrypted SQLite Persistent Storage,
Inverted Keyword Indexing, Explicit Consent Gatekeeping, and Versioning.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from core.exceptions import SecurityError
from memory.crypto import AuthenticatedEncryptor, BaseEncryptor
from memory.indexing import KeywordMemoryIndex, MemoryIndex
from memory.long_term import (
    ConsentStatus,
    MemoryRecord,
    MemoryType,
    RetentionPolicy,
    SensitivityLevel,
)
from memory.sqlite_store import SQLiteMemoryStore
from memory.working import WorkingMemory
from model_routing.schemas import ChatMessage
from security.audit_logger import AuditLogger


class MemoryManager:
    """Orchestrator for working context, encrypted persistent memory, and consent enforcement."""

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        encryptor: BaseEncryptor | None = None,
        audit_logger: AuditLogger | None = None,
        max_working_items: int = 20,
        max_memory_records: int = 1000,
        max_content_length: int = 4000,
        max_query_length: int = 500,
    ) -> None:
        self.max_memory_records = max_memory_records
        self.max_content_length = max_content_length
        self.max_query_length = max_query_length

        self.working_memory = WorkingMemory(max_items=max_working_items)
        self.encryptor = encryptor or AuthenticatedEncryptor()
        self.store = SQLiteMemoryStore(db_path=db_path, encryptor=self.encryptor)
        self.index: MemoryIndex = KeywordMemoryIndex()
        self.audit = audit_logger or AuditLogger()

        # Hydrate index from active store records
        self._hydrate_index()

    def _hydrate_index(self) -> None:
        """Load all active records into in-memory search index on startup."""
        records = self.store.list_records(include_inactive=False, limit=self.max_memory_records)
        for rec in records:
            self.index.index_record(rec)

    # -------------------------------------------------------------------------
    # 1. Working Memory (Ephemeral Session RAM)
    # -------------------------------------------------------------------------

    def add_working_message(self, message: ChatMessage) -> None:
        """Append message turn to working context."""
        self.working_memory.add_message(message)

    def get_working_messages(self) -> list[ChatMessage]:
        """Retrieve recent conversation turns."""
        return self.working_memory.get_messages()

    def clear_working_memory(self) -> None:
        """Flush in-memory working buffer."""
        self.working_memory.clear()

    # -------------------------------------------------------------------------
    # 2. Explicit Consent & Persistent Memory Creation
    # -------------------------------------------------------------------------

    async def remember_explicit(
        self,
        content: str,
        category: MemoryType = MemoryType.SEMANTIC,
        sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        session_id: str = "default_session",
        tags: list[str] | None = None,
        retention_policy: RetentionPolicy = RetentionPolicy.PERMANENT,
        retention_days: int = 0,
    ) -> MemoryRecord:
        """Persist a memory explicitly requested and approved by the user."""
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]

        record = MemoryRecord(
            category=category,
            content=content,
            source_session_id=session_id,
            consent_status=ConsentStatus.EXPLICIT_APPROVED,
            sensitivity=sensitivity,
            retention_policy=retention_policy,
            retention_days=retention_days,
            tags=tags or [],
            version=1,
            is_active=True,
        )

        self.store.save_record(record)
        self.index.index_record(record)

        # Audit metadata only - NEVER plaintext content
        self.audit.log(
            actor_id="user_explicit",
            session_id=session_id,
            action_type="MEMORY_CREATE_EXPLICIT",
            event_type="MEMORY_OPERATION",
            risk_level=sensitivity.value,
            target_resource=str(record.memory_id),
            parameters={
                "category": category.value,
                "sensitivity": sensitivity.value,
                "version": 1,
                "tag_count": len(record.tags),
            },
            decision="STORED",
        )

        return record

    def propose_memory_suggestion(
        self,
        content: str,
        category: MemoryType = MemoryType.SEMANTIC,
        sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        session_id: str = "default_session",
        tags: list[str] | None = None,
    ) -> MemoryRecord:
        """Create an unpersisted candidate record proposed by assistant, awaiting human consent."""
        return MemoryRecord(
            category=category,
            content=content,
            source_session_id=session_id,
            consent_status=ConsentStatus.MODEL_SUGGESTED,
            sensitivity=sensitivity,
            tags=tags or [],
            is_active=False,  # Inactive until approved
        )

    async def approve_suggested_memory(self, suggestion: MemoryRecord) -> MemoryRecord:
        """Approve and persist a previously suggested memory record."""
        approved = suggestion.model_copy(
            update={
                "consent_status": ConsentStatus.EXPLICIT_APPROVED,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self.store.save_record(approved)
        self.index.index_record(approved)

        self.audit.log(
            actor_id="user_approval",
            session_id=approved.source_session_id,
            action_type="MEMORY_APPROVE_SUGGESTION",
            event_type="MEMORY_OPERATION",
            risk_level=approved.sensitivity.value,
            target_resource=str(approved.memory_id),
            parameters={"category": approved.category.value},
            decision="STORED",
        )
        return approved

    # -------------------------------------------------------------------------
    # 3. Retrieval with Access & Sensitivity Controls
    # -------------------------------------------------------------------------

    async def recall(
        self,
        query: str,
        category: MemoryType | None = None,
        max_sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        session_id: str = "default_session",
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """Search persistent memories matching query, respecting sensitivity bounds."""
        if not query:
            return []

        clean_query = query[:self.max_query_length]

        # Query index first for sub-millisecond keyword lookup
        results = self.index.search(
            query=clean_query,
            category=category,
            max_sensitivity=max_sensitivity,
            limit=limit,
        )

        # Fall back to SQLite search if index is empty
        if not results:
            results = self.store.search_records(
                keyword=clean_query,
                category=category,
                max_sensitivity=max_sensitivity,
                limit=limit,
            )

        # Audit retrieval metadata
        self.audit.log(
            actor_id="agent_recall",
            session_id=session_id,
            action_type="MEMORY_RECALL",
            event_type="MEMORY_OPERATION",
            risk_level=max_sensitivity.value,
            target_resource="memory_index",
            parameters={
                "query_len": len(clean_query),
                "results_count": len(results),
                "max_sensitivity": max_sensitivity.value,
            },
            decision="SUCCESS",
        )

        return results

    # -------------------------------------------------------------------------
    # 4. Versioning & Updating Memories
    # -------------------------------------------------------------------------

    async def update_memory(
        self,
        memory_id: UUID,
        new_content: str,
        session_id: str = "default_session",
    ) -> MemoryRecord:
        """Update existing memory, deactivating stale version and incrementing version number."""
        old_record = self.store.get_record(memory_id)
        if not old_record:
            raise KeyError(f"Memory with ID '{memory_id}' not found.")

        updated_record = old_record.mark_updated(new_content)
        self.store.save_record(updated_record)
        self.index.index_record(updated_record)

        self.audit.log(
            actor_id="user_explicit",
            session_id=session_id,
            action_type="MEMORY_UPDATE",
            event_type="MEMORY_OPERATION",
            risk_level=updated_record.sensitivity.value,
            target_resource=str(memory_id),
            parameters={"new_version": updated_record.version},
            decision="UPDATED",
        )

        return updated_record

    # -------------------------------------------------------------------------
    # 5. Inspection & Transparency
    # -------------------------------------------------------------------------

    def inspect_memory(self, memory_id: UUID) -> MemoryRecord | None:
        """Inspect single memory provenance and metadata."""
        return self.store.get_record(memory_id)

    def list_all_memories(
        self,
        category: MemoryType | None = None,
        max_sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        """List all active stored memories within sensitivity bounds."""
        records = self.store.list_records(category=category, include_inactive=False, limit=limit)
        return [
            r for r in records
            if not (r.sensitivity == SensitivityLevel.SENSITIVE and max_sensitivity != SensitivityLevel.SENSITIVE)
        ]

    # -------------------------------------------------------------------------
    # 6. Memory Deletion ("Right to be Forgotten")
    # -------------------------------------------------------------------------

    async def forget_memory(self, memory_id: UUID, session_id: str = "default_session") -> bool:
        """Delete specific memory from SQLite, index, and caches."""
        self.index.remove_record(memory_id)
        deleted = self.store.delete_record(memory_id)

        self.audit.log(
            actor_id="user_explicit",
            session_id=session_id,
            action_type="MEMORY_DELETE",
            event_type="MEMORY_OPERATION",
            risk_level="NORMAL",
            target_resource=str(memory_id),
            parameters={"is_deleted": deleted},
            decision="DELETED" if deleted else "NOT_FOUND",
        )

        return deleted

    async def forget_by_topic(self, topic: str, session_id: str = "default_session") -> int:
        """Purge memories matching topic across store and index."""
        # Find matching in index and remove
        matching = self.index.search(topic, limit=1000)
        for rec in matching:
            self.index.remove_record(rec.memory_id)

        count = self.store.delete_records_by_topic(topic)

        self.audit.log(
            actor_id="user_explicit",
            session_id=session_id,
            action_type="MEMORY_DELETE_TOPIC",
            event_type="MEMORY_OPERATION",
            risk_level="NORMAL",
            target_resource=topic,
            parameters={"purged_count": count},
            decision="PURGED",
        )

        return count

    async def delete_all_memories(self, session_id: str = "default_session") -> None:
        """Factory reset all working and persistent memory."""
        self.working_memory.clear()
        self.index.clear()
        self.store.clear_all()

        self.audit.log(
            actor_id="user_explicit",
            session_id=session_id,
            action_type="MEMORY_DELETE_ALL",
            event_type="MEMORY_OPERATION",
            risk_level="SENSITIVE",
            target_resource="all_memories",
            parameters={},
            decision="WIPED",
        )
