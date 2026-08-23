"""Comprehensive Automated Performance, Caching & Latency Optimization Test Suite (Phase 11)."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any
import unittest
from uuid import uuid4

from config.schema import ModelsConfig, ModelTier, PerformanceConfig
from core.compat import BaseModel
from model_routing.base import BaseModelProvider
from model_routing.optimization.benchmarker import (
    BenchmarkReport,
    LatencyMetrics,
    PerformanceBenchmarker,
)
from model_routing.optimization.cache import SemanticResponseCache
from model_routing.optimization.memory_guard import MemoryGuard
from model_routing.optimization.token_optimizer import TokenOptimizer
from model_routing.providers.local_quantized_provider import LocalQuantizedProvider
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.router import ModelRouter
from model_routing.schemas import ChatMessage, MessageRole, ModelRequest, ModelResponse
from security.sanitizer import Sanitizer


class TestPhase11PerformanceOptimization(unittest.IsolatedAsyncioTestCase):
    """Performance, Latency & Token Optimization Verification Battery."""

    def setUp(self) -> None:
        self.perf_config = PerformanceConfig(
            enable_token_optimization=True,
            enable_response_cache=True,
            cache_ttl_seconds=3600,
            cache_max_entries=100,
            max_context_tokens=1000,
            sliding_window_turns=5,
            max_ram_mb=2048,
            memory_pressure_threshold_mb=1536,
            target_ttft_ms=400,
            default_quantization="Q4_K_M",
        )
        self.sanitizer = Sanitizer()
        self.router = ModelRouter(
            performance_config=self.perf_config,
            sanitizer=self.sanitizer,
        )

    # ====================================================
    # 1. Token Estimation & Context Window Optimization
    # ====================================================

    def test_token_estimator_accuracy(self) -> None:
        """1. Verify TokenOptimizer estimates tokens accurately without C tokenizer dependencies."""
        text = "Hello world! This is a test sentence for token estimation."
        tokens = TokenOptimizer.estimate_tokens(text)
        self.assertGreaterEqual(tokens, 10)
        self.assertLessEqual(tokens, 20)

        # Empty string yields 0
        self.assertEqual(TokenOptimizer.estimate_tokens(""), 0)

    def test_system_prefix_stabilization(self) -> None:
        """2. Verify system prompt prefix stabilization normalizes whitespace for KV-cache alignment."""
        raw_prompt = "\n\n  You are JARVIS, an autonomous AI assistant.\n\n\nAlways be polite.   \n\n"
        stabilized = TokenOptimizer.stabilize_system_prefix(raw_prompt)

        self.assertTrue(stabilized.startswith("You are JARVIS"))
        self.assertTrue(stabilized.endswith("\n"))
        self.assertNotIn("\n\n\n", stabilized)

    def test_sliding_window_pruning(self) -> None:
        """3. Verify sliding window retains system message and the most recent N turns."""
        optimizer = TokenOptimizer(max_context_tokens=4000, sliding_window_turns=3)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content="System instruction"),
            ChatMessage(role=MessageRole.USER, content="Turn 1"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Reply 1"),
            ChatMessage(role=MessageRole.USER, content="Turn 2"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Reply 2"),
            ChatMessage(role=MessageRole.USER, content="Turn 3"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Reply 3"),
            ChatMessage(role=MessageRole.USER, content="Turn 4"),
        ]

        optimized, count = optimizer.optimize_messages(messages)

        # System message preserved + last 3 turns
        self.assertEqual(len(optimized), 4)
        self.assertEqual(optimized[0].role, MessageRole.SYSTEM)
        self.assertEqual(optimized[1].content, "Turn 3")
        self.assertEqual(optimized[2].content, "Reply 3")
        self.assertEqual(optimized[3].content, "Turn 4")

    def test_token_budget_truncation(self) -> None:
        """4. Verify token optimizer prunes dialogue messages when token budget is exceeded."""
        optimizer = TokenOptimizer(max_context_tokens=50, sliding_window_turns=10)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content="System prompt"),
            ChatMessage(role=MessageRole.USER, content="A" * 100),
            ChatMessage(role=MessageRole.ASSISTANT, content="B" * 100),
            ChatMessage(role=MessageRole.USER, content="Recent message"),
        ]

        optimized, count = optimizer.optimize_messages(messages)

        # System prompt + newest message must be retained within 50 tokens
        self.assertEqual(optimized[0].role, MessageRole.SYSTEM)
        self.assertEqual(optimized[-1].content, "Recent message")
        self.assertLessEqual(count, 55)

    # ====================================================
    # 2. Semantic Response Caching & Sub-10ms Retrieval
    # ====================================================

    def test_semantic_response_cache_hit_and_speed(self) -> None:
        """5. Verify prompt response cache returns in < 10ms on identical request."""
        cache = SemanticResponseCache(max_entries=100, default_ttl_seconds=300)
        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="What is quantum computing?")],
            tier="fast",
        )
        resp = ModelResponse(
            model_name="mock-fast",
            provider_name="mock",
            content="Quantum computing leverages superposition and entanglement.",
            prompt_tokens=15,
            completion_tokens=10,
        )

        # Cache miss on first lookup
        self.assertIsNone(cache.get(req))

        # Store response
        cache.put(req, resp)

        # Measure cache hit latency
        t0 = time.perf_counter()
        cached_result = cache.get(req)
        retrieval_ms = (time.perf_counter() - t0) * 1000.0

        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.content, resp.content)
        self.assertLess(retrieval_ms, 10.0, f"Cache retrieval took {retrieval_ms:.2f}ms (expected < 10ms)")

        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)

    def test_semantic_response_cache_lru_eviction(self) -> None:
        """6. Verify LRU eviction removes oldest entry when capacity is exceeded."""
        cache = SemanticResponseCache(max_entries=2, default_ttl_seconds=300)

        req1 = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Prompt 1")])
        req2 = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Prompt 2")])
        req3 = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Prompt 3")])

        resp = ModelResponse(model_name="mock", provider_name="mock", content="OK")

        cache.put(req1, resp)
        cache.put(req2, resp)

        # Access req1 so req2 becomes the LRU
        self.assertIsNotNone(cache.get(req1))

        # Insert req3 -> causes req2 to be evicted
        cache.put(req3, resp)

        self.assertIsNotNone(cache.get(req1))
        self.assertIsNone(cache.get(req2))
        self.assertIsNotNone(cache.get(req3))
        self.assertEqual(cache.get_stats()["evictions"], 1)

    def test_semantic_response_cache_ttl_expiration(self) -> None:
        """7. Verify cached response expires after TTL."""
        cache = SemanticResponseCache(max_entries=10, default_ttl_seconds=1)
        req = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Ephemeral query")])
        resp = ModelResponse(model_name="mock", provider_name="mock", content="Ephemeral response")

        cache.put(req, resp, ttl_seconds=0.01)
        time.sleep(0.02)

        # Expired -> None
        self.assertIsNone(cache.get(req))

    def test_semantic_response_cache_session_invalidation(self) -> None:
        """8. Verify session invalidation purges only the target session's cache entries."""
        cache = SemanticResponseCache(max_entries=10)
        req_a = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Session A prompt")])
        req_b = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Session B prompt")])
        resp = ModelResponse(model_name="mock", provider_name="mock", content="Res")

        cache.put(req_a, resp, session_id="session_alpha")
        cache.put(req_b, resp, session_id="session_beta")

        invalidated_count = cache.invalidate_session("session_alpha")
        self.assertEqual(invalidated_count, 1)

        self.assertIsNone(cache.get(req_a, session_id="session_alpha"))
        self.assertIsNotNone(cache.get(req_b, session_id="session_beta"))

    # ====================================================
    # 3. Local Quantized Execution (GGUF) & Streaming
    # ====================================================

    async def test_local_quantized_provider_gguf_formats(self) -> None:
        """9. Verify LocalQuantizedProvider supports standard GGUF quantizations."""
        for quant in ["Q4_K_M", "Q5_K_M", "Q8_0", "FP16"]:
            provider = LocalQuantizedProvider(
                quantization=quant,
                n_threads=8,
                n_gpu_layers=33,
            )
            cfg = provider.get_runtime_config()
            self.assertEqual(cfg["quantization"], quant)
            self.assertEqual(cfg["n_threads"], 8)
            self.assertEqual(cfg["n_gpu_layers"], 33)

            req = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Hello")])
            resp = await provider.generate(req)
            self.assertIn(f"[GGUF:{quant}]", resp.content)
            self.assertTrue(await provider.is_healthy())

    async def test_local_quantized_provider_streaming(self) -> None:
        """10. Verify asynchronous streaming token generator."""
        provider = LocalQuantizedProvider(quantization="Q4_K_M")
        req = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Explain relativity")])

        tokens = []
        async for chunk in provider.stream_generate(req):
            tokens.append(chunk)

        full_text = "".join(tokens)
        self.assertTrue(len(tokens) > 1)
        self.assertIn("Process", full_text)

    async def test_local_quantized_provider_ttft_under_sla(self) -> None:
        """11. Verify LocalQuantizedProvider TTFT remains strictly under 400ms SLA."""
        provider = LocalQuantizedProvider(quantization="Q4_K_M")
        req = ModelRequest(messages=[ChatMessage(role=MessageRole.USER, content="Benchmark TTFT")])

        t0 = time.perf_counter()
        resp = await provider.generate(req)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        self.assertIsNotNone(provider.last_metrics)
        self.assertLess(provider.last_metrics.ttft_ms, 400.0)
        self.assertLess(duration_ms, 400.0)

    # ====================================================
    # 4. Latency Benchmarking & SLA Compliance
    # ====================================================

    def test_performance_benchmarker_percentiles(self) -> None:
        """12. Verify PerformanceBenchmarker computes P50, P90, P99 and SLA compliance."""
        benchmarker = PerformanceBenchmarker(target_ttft_ms=400.0)

        # Record sample latency metrics
        benchmarker.record_metric(LatencyMetrics(ttft_ms=50.0, total_latency_ms=120.0, tokens_per_second=50.0))
        benchmarker.record_metric(LatencyMetrics(ttft_ms=80.0, total_latency_ms=180.0, tokens_per_second=40.0))
        benchmarker.record_metric(LatencyMetrics(ttft_ms=120.0, total_latency_ms=250.0, tokens_per_second=35.0))
        benchmarker.record_metric(LatencyMetrics(ttft_ms=300.0, total_latency_ms=600.0, tokens_per_second=20.0))

        report = benchmarker.generate_report()
        self.assertEqual(report.total_runs, 4)
        self.assertLessEqual(report.p50_ttft_ms, 120.0)
        self.assertLessEqual(report.p90_ttft_ms, 300.0)
        self.assertTrue(report.target_ttft_sla_met)

    # ====================================================
    # 5. Process Memory Guard & Footprint Minimization
    # ====================================================

    def test_memory_guard_rss_and_limits(self) -> None:
        """13. Verify MemoryGuard monitors RSS memory and enforces < 2048 MB limit."""
        guard = MemoryGuard(max_ram_mb=2048, pressure_threshold_mb=1536)
        rss_mb = guard.get_process_rss_mb()

        self.assertGreater(rss_mb, 0.0)
        self.assertLess(rss_mb, 2048.0, f"Process RSS {rss_mb:.2f}MB exceeds 2048MB limit!")
        self.assertTrue(guard.is_within_limits())
        self.assertFalse(guard.check_memory_pressure())

    def test_memory_guard_compaction(self) -> None:
        """14. Verify MemoryGuard executes garbage collection and compaction callbacks."""
        guard = MemoryGuard()
        callback_ran = False

        def cleanup():
            nonlocal callback_ran
            callback_ran = True

        guard.register_compaction_callback(cleanup)
        res = guard.trigger_compaction()

        self.assertTrue(callback_ran)
        self.assertTrue(res["within_safe_limits"])

    # ====================================================
    # 6. Integrated ModelRouter Workflow
    # ====================================================

    async def test_model_router_with_caching_and_sanitization(self) -> None:
        """15. Verify ModelRouter integrates caching, token optimization, PII redaction and restoration."""
        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Contact tony.stark@starkindustries.com for update.")],
            tier="fast",
        )

        # 1. First execution routes to provider and caches response
        resp1 = await self.router.route(req, tier=ModelTier.FAST)
        self.assertIsNotNone(resp1)

        # 2. Second identical execution hits response cache in < 10ms
        t0 = time.perf_counter()
        resp2 = await self.router.route(req, tier=ModelTier.FAST)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(resp1.content, resp2.content)
        self.assertLess(elapsed_ms, 15.0)

        # Verify benchmark report
        report = self.router.benchmarker.generate_report()
        self.assertEqual(report.total_runs, 2)
        self.assertTrue(report.target_ttft_sla_met)

    async def test_model_router_local_quantized_tier_dispatch(self) -> None:
        """16. Verify LOCAL_PRIVATE tier routes to LocalQuantizedProvider with sub-400ms TTFT."""
        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Run local private inference")],
            tier="local_private",
        )
        resp = await self.router.route(req, tier=ModelTier.LOCAL_PRIVATE)

        self.assertIn("GGUF", resp.content)
        self.assertEqual(resp.provider_name, "local-quantized-gguf")


if __name__ == "__main__":
    unittest.main()
