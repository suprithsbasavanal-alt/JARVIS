"""Performance Benchmarking, Latency Metrics, and TTFT Profiling (Phase 11)."""

from dataclasses import dataclass, field
import statistics
import time
from typing import Any
from model_routing.schemas import ModelRequest, ModelResponse


@dataclass
class LatencyMetrics:
    """Latency and token throughput measurement for a single inference request."""
    ttft_ms: float = 0.0          # Time to first token in milliseconds
    total_latency_ms: float = 0.0  # Total end-to-end duration in milliseconds
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tokens_per_second: float = 0.0
    tier: str = "fast"
    is_cached: bool = False


@dataclass
class BenchmarkReport:
    """Aggregated latency and throughput report across multiple inference runs."""
    total_runs: int = 0
    p50_ttft_ms: float = 0.0
    p90_ttft_ms: float = 0.0
    p99_ttft_ms: float = 0.0
    mean_ttft_ms: float = 0.0
    p50_total_ms: float = 0.0
    p90_total_ms: float = 0.0
    mean_total_ms: float = 0.0
    mean_tokens_per_second: float = 0.0
    target_ttft_sla_met: bool = True


class PerformanceBenchmarker:
    """Profiles TTFT, throughput, and SLA compliance for model routing and execution."""

    def __init__(self, target_ttft_ms: float = 400.0) -> None:
        self.target_ttft_ms = target_ttft_ms
        self._metrics_history: list[LatencyMetrics] = []

    def record_metric(self, metric: LatencyMetrics) -> None:
        """Record an individual request latency measurement."""
        self._metrics_history.append(metric)

    def generate_report(self) -> BenchmarkReport:
        """Calculate percentile metrics and SLA compliance from recorded measurements."""
        if not self._metrics_history:
            return BenchmarkReport(total_runs=0, target_ttft_sla_met=True)

        ttft_values = [m.ttft_ms for m in self._metrics_history]
        total_values = [m.total_latency_ms for m in self._metrics_history]
        tps_values = [m.tokens_per_second for m in self._metrics_history if m.tokens_per_second > 0]

        ttft_sorted = sorted(ttft_values)
        total_sorted = sorted(total_values)

        def percentile(data: list[float], pct: float) -> float:
            if not data:
                return 0.0
            idx = int(len(data) * pct)
            return data[min(idx, len(data) - 1)]

        p50_ttft = percentile(ttft_sorted, 0.50)
        p90_ttft = percentile(ttft_sorted, 0.90)
        p99_ttft = percentile(ttft_sorted, 0.99)
        mean_ttft = statistics.mean(ttft_values) if ttft_values else 0.0

        p50_total = percentile(total_sorted, 0.50)
        p90_total = percentile(total_sorted, 0.90)
        mean_total = statistics.mean(total_values) if total_values else 0.0
        mean_tps = statistics.mean(tps_values) if tps_values else 0.0

        sla_met = p90_ttft <= self.target_ttft_ms

        return BenchmarkReport(
            total_runs=len(self._metrics_history),
            p50_ttft_ms=round(p50_ttft, 2),
            p90_ttft_ms=round(p90_ttft, 2),
            p99_ttft_ms=round(p99_ttft, 2),
            mean_ttft_ms=round(mean_ttft, 2),
            p50_total_ms=round(p50_total, 2),
            p90_total_ms=round(p90_total, 2),
            mean_total_ms=round(mean_total, 2),
            mean_tokens_per_second=round(mean_tps, 2),
            target_ttft_sla_met=sla_met,
        )

    def clear(self) -> None:
        """Clear recorded benchmark metrics."""
        self._metrics_history.clear()
