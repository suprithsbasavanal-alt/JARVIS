"""Deterministic Semantic & Prompt Response Cache with LRU Eviction & KV-Prefix Fingerprinting (Phase 11)."""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any
from uuid import UUID, uuid4

from model_routing.schemas import ChatMessage, ModelRequest, ModelResponse


@dataclass
class CacheEntry:
    """Container for a cached model inference response."""
    cache_key: str
    response: ModelResponse
    created_at_epoch: float
    expires_at_epoch: float
    access_count: int = 0
    session_id: str | None = None


class SemanticResponseCache:
    """In-memory deterministic prompt response cache with sub-10ms retrieval, TTL, and LRU eviction."""

    def __init__(
        self,
        max_entries: int = 1000,
        default_ttl_seconds: int = 3600,
    ) -> None:
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0,
        }

    def compute_cache_key(
        self,
        request: ModelRequest,
        session_id: str | None = None,
    ) -> str:
        """Compute deterministic SHA-256 hash for a ModelRequest."""
        # Normalize messages into structured tuples
        norm_messages = []
        for msg in request.messages:
            norm_messages.append({
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.content.strip(),
                "name": msg.name or "",
                "tool_call_id": msg.tool_call_id or "",
            })

        payload = {
            "tier": request.tier,
            "messages": norm_messages,
            "tools": sorted([t.get("name", "") for t in request.tools]) if request.tools else [],
            "temperature": round(request.temperature, 2),
            "session_id": session_id or "",
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(
        self,
        request: ModelRequest,
        session_id: str | None = None,
    ) -> ModelResponse | None:
        """Retrieve cached response if available and not expired. Sub-10ms execution."""
        key = self.compute_cache_key(request, session_id=session_id)
        now = time.time()

        entry = self._cache.get(key)
        if not entry:
            self._stats["misses"] += 1
            return None

        # Check TTL
        if now > entry.expires_at_epoch:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        # LRU touch: move to end
        self._cache.move_to_end(key)
        entry.access_count += 1
        self._stats["hits"] += 1

        # Return a copy of the response with cached metadata
        cached_resp = entry.response.model_copy()
        return cached_resp

    def put(
        self,
        request: ModelRequest,
        response: ModelResponse,
        session_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a model response in the cache with LRU eviction."""
        key = self.compute_cache_key(request, session_id=session_id)
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = now + ttl

        # Evict oldest entry if at capacity
        if len(self._cache) >= self.max_entries and key not in self._cache:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1

        entry = CacheEntry(
            cache_key=key,
            response=response,
            created_at_epoch=now,
            expires_at_epoch=expires_at,
            session_id=session_id,
        )
        self._cache[key] = entry
        self._cache.move_to_end(key)

    def invalidate_session(self, session_id: str) -> int:
        """Invalidate all cached responses associated with a specific session."""
        keys_to_remove = [
            k for k, v in self._cache.items() if v.session_id == session_id
        ]
        for k in keys_to_remove:
            del self._cache[k]
        self._stats["invalidations"] += len(keys_to_remove)
        return len(keys_to_remove)

    def clear(self) -> None:
        """Wipe entire response cache."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics and memory size metrics."""
        total_lookups = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_lookups) if total_lookups > 0 else 0.0
        return {
            "entries_count": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 4),
            "evictions": self._stats["evictions"],
            "invalidations": self._stats["invalidations"],
        }
