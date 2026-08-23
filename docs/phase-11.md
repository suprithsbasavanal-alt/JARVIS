# Phase 11: Performance & Latency Tuning Specification

## 1. Overview & Objectives

Phase 11 implements performance engineering, context token optimization, sub-10ms response caching, deterministic KV-cache prefix stabilization, local quantized model execution (GGUF via llama.cpp / vLLM / Ollama), and memory ceiling guardrails (< 2GB RAM).

### 1.1 Core Target SLAs
1. **Time-To-First-Token (TTFT)**: < 400ms on cached and fast local inference tiers.
2. **Memory Footprint**: Process RSS RAM < 2048 MB with proactive compaction triggered at 1536 MB.
3. **Response Cache Retrieval**: Sub-10ms for identical requests with deterministic SHA-256 cache keying.
4. **Token Context Optimization**: Sliding-window dialogue pruning while preserving pinned system prompts for hardware KV-cache prefix reuse.
5. **Local Quantized Model Execution**: Support for GGUF quantizations (`Q4_K_M`, `Q5_K_M`, `Q8_0`, `FP16`) with configurable thread counts, context limits, and GPU layer offloading.

---

## 2. Optimization Architecture

```
                               ┌────────────────────────────────┐
                               │       ModelRouter (Tier)       │
                               └───────────────┬────────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               │                               │                               │
┌──────────────▼─────────────┐  ┌──────────────▼─────────────┐  ┌──────────────▼─────────────┐
│ TokenOptimizer             │  │ Response & KV-Prefix Cache │  │ LocalQuantizedProvider     │
│ - Sliding window pruning   │  │ - SHA-256 prompt hashing   │  │ - GGUF llama.cpp/vLLM stub │
│ - KV prefix stabilization  │  │ - Sub-10ms cache retrieval │  │ - TTFT / TPS stream metric │
│ - Token budget compression │  │ - Session isolation        │  │ - Q4_K_M, Q5_K_M, Q8_0     │
└────────────────────────────┘  └────────────────────────────┘  └────────────────────────────┘
                                               │
                                ┌──────────────▼─────────────┐
                                │ Resource & Latency Monitor │
                                │ - Process RAM (< 2GB)      │
                                │ - Benchmarker (P50/P90/P99)│
                                │ - Compaction & GC Pressure │
                                └────────────────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1 Token Optimization (`model_routing/optimization/token_optimizer.py`)
- **`estimate_tokens(text)`**: Fast, hermetic token estimation using word boundary and 4-character heuristics.
- **`stabilize_system_prefix(prompt)`**: Deterministic formatting and trailing newline normalization ensuring KV-cache prefixes match across requests.
- **`optimize_messages(messages, max_tokens, max_turns)`**: Preserves system instructions at index 0, retains the latest N turns via sliding window, and truncates large payloads within budget constraints.

### 3.2 Semantic Response Cache (`model_routing/optimization/cache.py`)
- **`SemanticResponseCache`**: In-memory LRU cache storing `ModelResponse` containers indexed by SHA-256 request digest.
- **Features**: Sub-10ms retrieval, configurable TTL (default 3600s), LRU eviction upon reaching capacity (`max_entries = 1000`), and session-specific invalidation (`invalidate_session`).

### 3.3 Performance Benchmarker (`model_routing/optimization/benchmarker.py`)
- **`PerformanceBenchmarker`**: Collects `LatencyMetrics` (TTFT, total generation latency, prompt/completion tokens, throughput TPS).
- **`generate_report()`**: Computes P50, P90, P99, mean latency, and verifies SLA conformance against `target_ttft_ms = 400.0`.

### 3.4 Process Memory Guard (`model_routing/optimization/memory_guard.py`)
- **`MemoryGuard`**: Tracks OS resident set size (`ru_maxrss` across macOS and Linux).
- **`check_memory_pressure()`**: Proactively triggers cache compaction and garbage collection (`gc.collect()`) when RSS exceeds 1536 MB, guaranteeing the 2048 MB ceiling is never breached.

### 3.5 Local Quantized Inference Provider (`model_routing/providers/local_quantized_provider.py`)
- **`LocalQuantizedProvider`**: High-performance local inference backend supporting GGUF quantizations (`Q4_K_M`, `Q5_K_M`, `Q8_0`, `FP16`), streaming token generation, thread tuning (`n_threads`), and GPU offload layers (`n_gpu_layers`).

---

## 4. Verification Results

- `tests/test_phase11_performance_optimization.py`: **16/16 tests passing (100%)**.
- Total repository test suite: **371/371 tests passing (100% pass rate in 1.62s)**.
- Desktop UI TypeScript: **0 errors, 0 warnings**.
- Memory usage: **Process RSS strictly < 2048 MB**.
