"""Multi-Tier Dynamic Model Router with Sanitization, Response Caching, Token Optimization & Latency Tracking (Phase 11)."""

import time
from typing import Any

from config.schema import ModelsConfig, ModelTier, PerformanceConfig
from core.exceptions import ModelRoutingError
from model_routing.base import BaseModelProvider
from model_routing.optimization.benchmarker import LatencyMetrics, PerformanceBenchmarker
from model_routing.optimization.cache import SemanticResponseCache
from model_routing.optimization.memory_guard import MemoryGuard
from model_routing.optimization.token_optimizer import TokenOptimizer
from model_routing.providers.local_quantized_provider import LocalQuantizedProvider
from model_routing.providers.mock_provider import MockModelProvider
from model_routing.schemas import ChatMessage, ModelRequest, ModelResponse
from security.sanitizer import Sanitizer


class ModelRouter:
    """Orchestrates model requests across Fast, Reasoning, and Local Private tiers with sub-second optimization."""

    def __init__(
        self,
        config: ModelsConfig | None = None,
        performance_config: PerformanceConfig | None = None,
        sanitizer: Sanitizer | None = None,
    ) -> None:
        self.config = config or ModelsConfig()
        self.perf_config = performance_config or PerformanceConfig()
        self.sanitizer = sanitizer or Sanitizer()

        # Optimization & caching subsystems
        self.token_optimizer = TokenOptimizer(
            max_context_tokens=self.perf_config.max_context_tokens,
            sliding_window_turns=self.perf_config.sliding_window_turns,
        )
        self.response_cache = SemanticResponseCache(
            max_entries=self.perf_config.cache_max_entries,
            default_ttl_seconds=self.perf_config.cache_ttl_seconds,
        )
        self.benchmarker = PerformanceBenchmarker(
            target_ttft_ms=float(self.perf_config.target_ttft_ms)
        )
        self.memory_guard = MemoryGuard(
            max_ram_mb=self.perf_config.max_ram_mb,
            pressure_threshold_mb=self.perf_config.memory_pressure_threshold_mb,
        )
        # Register cache clearing on memory pressure
        self.memory_guard.register_compaction_callback(self.response_cache.clear)

        self._providers: dict[str, BaseModelProvider] = {}
        # Register default fallback mock provider
        self.register_provider("mock", MockModelProvider("mock"))
        # Register high-performance local quantized GGUF provider
        local_quant_prov = LocalQuantizedProvider(
            quantization=self.perf_config.default_quantization,
            n_threads=self.perf_config.n_threads,
            n_gpu_layers=self.perf_config.n_gpu_layers,
            n_ctx=self.perf_config.max_context_tokens,
        )
        self.register_provider("local-quantized", local_quant_prov)
        self.register_provider("local", local_quant_prov)

    def register_provider(self, name: str, provider: BaseModelProvider) -> None:
        """Register a model execution provider."""
        self._providers[name] = provider

    def get_provider_for_tier(self, tier: ModelTier) -> BaseModelProvider:
        """Resolve the appropriate provider backend for the requested tier."""
        tier_config_map = {
            ModelTier.FAST: self.config.fast_tier,
            ModelTier.REASONING: self.config.reasoning_tier,
            ModelTier.LOCAL_PRIVATE: self.config.local_private_tier,
        }
        tier_cfg = tier_config_map.get(tier, self.config.fast_tier)

        if tier == ModelTier.LOCAL_PRIVATE:
            if "local-quantized" in self._providers:
                return self._providers["local-quantized"]
            if "local" in self._providers:
                return self._providers["local"]

        provider = self._providers.get(tier_cfg.provider)

        if not provider:
            # Fall back to mock provider in development
            provider = self._providers.get("mock")
            if not provider:
                raise ModelRoutingError(f"No provider available for tier '{tier.value}'")

        return provider

    async def route(
        self,
        request: ModelRequest,
        tier: ModelTier = ModelTier.FAST,
        enable_sanitization: bool = True,
        enable_caching: bool = True,
        session_id: str | None = None,
    ) -> ModelResponse:
        """Route request through token optimization, response caching, sanitization, and execution."""
        start_time = time.perf_counter()

        # 1. Check response cache if enabled
        if enable_caching and self.perf_config.enable_response_cache:
            cached = self.response_cache.get(request, session_id=session_id)
            if cached:
                cached_latency_ms = (time.perf_counter() - start_time) * 1000.0
                self.benchmarker.record_metric(
                    LatencyMetrics(
                        ttft_ms=round(cached_latency_ms, 2),
                        total_latency_ms=round(cached_latency_ms, 2),
                        prompt_tokens=cached.prompt_tokens,
                        completion_tokens=cached.completion_tokens,
                        tokens_per_second=10000.0,
                        tier=tier.value,
                        is_cached=True,
                    )
                )
                return cached

        # 2. Token context pruning & KV-prefix stabilization
        if self.perf_config.enable_token_optimization:
            optimized_messages, _ = self.token_optimizer.optimize_messages(request.messages)
            exec_request = request.model_copy(update={"messages": optimized_messages})
        else:
            exec_request = request

        # 3. Sanitize prompt if enabled
        if enable_sanitization and self.sanitizer:
            sanitized_messages: list[ChatMessage] = []
            for msg in exec_request.messages:
                sanitized_content = self.sanitizer.sanitize(msg.content)
                sanitized_messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=sanitized_content,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            exec_request = exec_request.model_copy(update={"messages": sanitized_messages})

        # 4. Resolve provider and execute inference
        provider = self.get_provider_for_tier(tier)
        inf_start = time.perf_counter()
        response = await provider.generate(exec_request)
        inf_duration_ms = (time.perf_counter() - inf_start) * 1000.0

        # Estimate tokens if not populated by provider
        if response.prompt_tokens == 0:
            response.prompt_tokens = TokenOptimizer.estimate_messages_tokens(exec_request.messages)
        if response.completion_tokens == 0 and response.content:
            response.completion_tokens = TokenOptimizer.estimate_tokens(response.content)

        # 5. Populate response cache if enabled
        if enable_caching and self.perf_config.enable_response_cache:
            self.response_cache.put(request, response, session_id=session_id)

        # 6. Restore sanitized placeholders in the output
        if enable_sanitization and self.sanitizer and response.content:
            restored_content = self.sanitizer.restore(response.content)
            response = response.model_copy(update={"content": restored_content})

        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        ttft_ms = inf_duration_ms * 0.4  # Approximate initial chunk time if not streaming
        tps = (
            (response.completion_tokens / (inf_duration_ms / 1000.0))
            if inf_duration_ms > 0
            else 0.0
        )

        self.benchmarker.record_metric(
            LatencyMetrics(
                ttft_ms=round(ttft_ms, 2),
                total_latency_ms=round(total_latency_ms, 2),
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                tokens_per_second=round(tps, 2),
                tier=tier.value,
                is_cached=False,
            )
        )

        # 7. Check memory pressure and compact if needed
        if self.memory_guard.check_memory_pressure():
            self.memory_guard.trigger_compaction()

        return response
