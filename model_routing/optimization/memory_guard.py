"""Process Memory Footprint Monitoring, Pressure Detection & Garbage Collection Compactor (Phase 11)."""

import gc
import os
import resource
import sys
from typing import Any, Callable


class MemoryGuard:
    """Monitors process memory footprint, detects memory pressure (> 1.5GB), and enforces < 2GB ceiling."""

    def __init__(
        self,
        max_ram_mb: int = 2048,
        pressure_threshold_mb: int = 1536,
    ) -> None:
        self.max_ram_mb = max_ram_mb
        self.pressure_threshold_mb = pressure_threshold_mb
        self._compaction_callbacks: list[Callable[[], None]] = []

    def register_compaction_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback (e.g. cache clearance) to be invoked during memory compaction."""
        self._compaction_callbacks.append(callback)

    def get_process_rss_mb(self) -> float:
        """Return current process resident set size (RSS) in megabytes."""
        try:
            # ru_maxrss returns kilobytes on Linux, bytes on macOS
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            if sys.platform == "darwin":
                # macOS returns bytes
                return rusage.ru_maxrss / (1024.0 * 1024.0)
            else:
                # Linux returns kilobytes
                return rusage.ru_maxrss / 1024.0
        except Exception:
            return 0.0

    def check_memory_pressure(self) -> bool:
        """Check if memory consumption exceeds the proactive pressure threshold (1.5GB)."""
        current_rss = self.get_process_rss_mb()
        return current_rss >= self.pressure_threshold_mb

    def is_within_limits(self) -> bool:
        """Verify process RAM is strictly below the 2048 MB (2 GB) ceiling."""
        current_rss = self.get_process_rss_mb()
        return current_rss < self.max_ram_mb

    def trigger_compaction(self) -> dict[str, Any]:
        """Execute garbage collection and trigger registered cache compactions."""
        before_rss = self.get_process_rss_mb()

        # 1. Run custom compaction callbacks (e.g. clear caches)
        for cb in self._compaction_callbacks:
            try:
                cb()
            except Exception:
                pass

        # 2. Force generational Python garbage collection
        unreachable = gc.collect()

        after_rss = self.get_process_rss_mb()

        return {
            "before_rss_mb": round(before_rss, 2),
            "after_rss_mb": round(after_rss, 2),
            "freed_mb": round(max(0.0, before_rss - after_rss), 2),
            "unreachable_objects_collected": unreachable,
            "within_safe_limits": after_rss < self.max_ram_mb,
        }
