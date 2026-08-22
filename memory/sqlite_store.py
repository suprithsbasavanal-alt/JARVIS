"""Persistent SQLite Storage Engine with Standard AEAD Field Encryption."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import UUID
from memory.crypto import AuthenticatedEncryptor, BaseEncryptor
from memory.long_term import (
    ConsentStatus,
    MemoryRecord,
    MemoryType,
    RetentionPolicy,
    SensitivityLevel,
)


class SQLiteMemoryStore:
    """ACID-compliant SQLite store for persistent memories with standard AEAD field encryption."""

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        encryptor: BaseEncryptor | None = None,
    ) -> None:
        self.db_path = str(db_path)
        self.encryptor = encryptor or AuthenticatedEncryptor()
        self._shared_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (shared for :memory:, fresh for disk files)."""
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_session_id TEXT NOT NULL,
                consent_status TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                encryption_status INTEGER NOT NULL,
                retention_policy TEXT NOT NULL,
                retention_days INTEGER NOT NULL,
                version INTEGER NOT NULL,
                is_active INTEGER NOT NULL,
                tags_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_sensitivity ON memories(sensitivity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(is_active)")
        conn.commit()
        if self._shared_conn is None:
            conn.close()

    def _generate_aad(self, memory_id: str | UUID, category: str | MemoryType, version: int) -> str:
        """Construct deterministic Authenticated Associated Data (AAD) string."""
        cat_val = category.value if isinstance(category, MemoryType) else str(category)
        return f"mid:{memory_id}|cat:{cat_val}|ver:{version}|enc:v2-aead"

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Deserialize database row into MemoryRecord with AEAD decryption and AAD verification."""
        is_encrypted = bool(row["encryption_status"])
        raw_content = row["content"]

        if is_encrypted:
            aad = self._generate_aad(row["memory_id"], row["category"], int(row["version"]))
            content = self.encryptor.decrypt(raw_content, associated_data=aad)
        else:
            content = raw_content

        return MemoryRecord(
            memory_id=UUID(row["memory_id"]),
            category=MemoryType(row["category"]),
            content=content,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source_session_id=row["source_session_id"],
            consent_status=ConsentStatus(row["consent_status"]),
            sensitivity=SensitivityLevel(row["sensitivity"]),
            encryption_status=is_encrypted,
            retention_policy=RetentionPolicy(row["retention_policy"]),
            retention_days=int(row["retention_days"]),
            version=int(row["version"]),
            is_active=bool(row["is_active"]),
            tags=json.loads(row["tags_json"]),
        )

    def save_record(self, record: MemoryRecord) -> None:
        """Persist or update memory record. Sensitive records are AEAD encrypted with AAD binding."""
        should_encrypt = record.sensitivity == SensitivityLevel.SENSITIVE or record.category == MemoryType.SENSITIVE
        if should_encrypt:
            aad = self._generate_aad(record.memory_id, record.category, record.version)
            stored_content = self.encryptor.encrypt(record.content, associated_data=aad)
            encryption_status = 1
        else:
            stored_content = record.content
            encryption_status = 0

        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO memories (
                memory_id, category, content, created_at, updated_at,
                source_session_id, consent_status, sensitivity, encryption_status,
                retention_policy, retention_days, version, is_active, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(record.memory_id),
                record.category.value,
                stored_content,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.source_session_id,
                record.consent_status.value,
                record.sensitivity.value,
                encryption_status,
                record.retention_policy.value,
                record.retention_days,
                record.version,
                1 if record.is_active else 0,
                json.dumps(record.tags),
            ),
        )
        conn.commit()
        if self._shared_conn is None:
            conn.close()

    def get_record(self, memory_id: UUID) -> MemoryRecord | None:
        """Retrieve single record by ID."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM memories WHERE memory_id = ?", (str(memory_id),))
        row = cursor.fetchone()
        rec = self._row_to_record(row) if row else None
        if self._shared_conn is None:
            conn.close()
        return rec

    def list_records(
        self,
        category: MemoryType | None = None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        """List stored memories with optional filtering."""
        query = "SELECT * FROM memories WHERE 1=1"
        params: list[object] = []

        if not include_inactive:
            query += " AND is_active = 1"
        if category:
            query += " AND category = ?"
            params.append(category.value)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        records: list[MemoryRecord] = []
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        for row in cursor.fetchall():
            records.append(self._row_to_record(row))
        if self._shared_conn is None:
            conn.close()
        return records

    def search_records(
        self,
        keyword: str,
        category: MemoryType | None = None,
        max_sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """Keyword search over active memories matching sensitivity bounds."""
        records = self.list_records(category=category, include_inactive=False, limit=200)
        results: list[MemoryRecord] = []
        kw_lower = keyword.lower()

        for rec in records:
            if rec.sensitivity == SensitivityLevel.SENSITIVE and max_sensitivity != SensitivityLevel.SENSITIVE:
                continue
            if kw_lower in rec.content.lower() or any(kw_lower in tag.lower() for tag in rec.tags):
                results.append(rec)
                if len(results) >= limit:
                    break

        return results

    def delete_record(self, memory_id: UUID) -> bool:
        """Permanently delete a memory record."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM memories WHERE memory_id = ?", (str(memory_id),))
        conn.commit()
        count = cursor.rowcount
        if self._shared_conn is None:
            conn.close()
        return count > 0

    def delete_records_by_topic(self, topic: str) -> int:
        """Delete memories where topic appears in tags or content."""
        to_delete: list[UUID] = []
        for rec in self.list_records(limit=1000):
            if topic.lower() in rec.content.lower() or any(topic.lower() in t.lower() for t in rec.tags):
                to_delete.append(rec.memory_id)

        conn = self._get_connection()
        for mid in to_delete:
            conn.execute("DELETE FROM memories WHERE memory_id = ?", (str(mid),))
        conn.commit()
        if self._shared_conn is None:
            conn.close()

        return len(to_delete)

    def clear_all(self) -> None:
        """Purge all stored memory records."""
        conn = self._get_connection()
        conn.execute("DELETE FROM memories")
        conn.commit()
        if self._shared_conn is None:
            conn.close()
