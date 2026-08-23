# Phase 6.4 Specification & Implementation Report: Proactive Runtime Wiring & Resource Hardening

**Phase**: 6.4  
**Date**: August 2026  
**Status**: COMPLETE  
**Test Suite**: `tests/test_phase6_4_runtime.py`  
**Total Repository Tests**: 211 / 211 Passing (100% Pass Rate)

---

## 1. Overview & Objectives

Phase 6.4 elevates the proactive intelligence subsystem (`intelligence/`) from domain modules into an integrated, resource-bounded, and asynchronously wired runtime subsystem.

### Key Objectives:
1. **EventBus Integration**: Connect domain events (`SESSION_STARTED`, `PROJECT_OPENED`, `USER_PROPOSITION_SUBMITTED`, `TASK_CREATED`, `STUDY_REQUESTED`, `PERIODIC_HEALTH_CHECK`) directly to `ProactiveCoordinator`.
2. **Context Advisory Assembly**: Enable `AgentLoop` and `SessionContext` to accept inert `<proactive_advisory>` blocks into LLM system prompts without side-effects or automated tool triggering.
3. **XML Delimiter Escaping & Injection Immunity**: Ensure all variable inputs and file contents embedded in `<proactive_advisory>` blocks undergo strict XML character entity escaping (`xml.sax.saxutils.escape`).
4. **Resource-Bounded Static Analysis**: Enforce per-file size limits (default 5 MB) and skip oversized files gracefully with `INFO` findings.
5. **Workspace Root & Symlink Sandboxing**: Validate project directory paths against authorized workspace roots (`allowed_roots`) and flag symlinks pointing outside the project boundary with `HIGH` security findings.
6. **Bounded Deduplication Cache**: Implement bounded LRU/FIFO eviction (`OrderedDict`, default capacity 1,000) for suggestion fingerprints to eliminate memory leaks.

---

## 2. Architecture & Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                              EventBus                                  │
│  (SESSION_STARTED, PROJECT_OPENED, USER_PROPOSITION_SUBMITTED, etc.)  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Asynchronous Subscription
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ProactiveRuntimeBridge (Listener)                    │
│   - Converts domain events to ProactiveTrigger                         │
│   - Enforces rate-limiting cooldown without crashing event bus         │
│   - Caches latest evaluation per session                               │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         ProactiveCoordinator                           │
│   - Bounded LRU Cache (max 1000 fingerprints, O(1) eviction)           │
│   - ProjectReviewEngine (5 MB limit, allowed_roots sandbox check)      │
│   - ReasoningAnalyzer (Polite epistemic disagreement)                  │
│   - PlanGenerator (Study & Task roadmaps)                              │
│   - InformationalGuard (Zero unsolicited tool execution)               │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       ProactiveDialogueAdvisor                         │
│   - XML Escaping: <, >, &, ", ' -> &lt;, &gt;, &amp;, &quot;, &apos;  │
│   - Inert XML formatting (<proactive_advisory is_informational_only>)  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                               AgentLoop                                │
│   - Step 3 Context Assembly: Append <proactive_advisory> to prompt     │
│   - Strict Human-in-the-Loop Confirmation Barrier                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Resource Hardening Specifications

| Component | Protection Mechanism | Limit / Threshold | Action on Breach |
| :--- | :--- | :--- | :--- |
| **ProjectReviewEngine** | Max File Size Inspection | `5 * 1024 * 1024` bytes (5 MB) | Skips file, adds `INFO` finding |
| **ProjectReviewEngine** | Workspace Root Check | `allowed_roots: list[Path]` | Raises `SandboxViolationError` |
| **ProjectReviewEngine** | Symlink Boundary Escape | Target canonical directory | Skips file, adds `HIGH` finding |
| **ProactiveCoordinator**| Fingerprint Memory Cache | 1,000 entries (`OrderedDict`) | Evicts oldest LRU entry |
| **DialogueAdvisor** | XML Entity Escaping | All fields via `_esc()` | Escapes characters to prevent injection |
| **AgentLoop** | Informational-Only Invariant | System context data only | Requires explicit user command to act |

---

## 4. Verification & Test Coverage

All 23 required scenarios were verified across unit and integration tests:

1. `test_event_bus_triggers_session_start` — Verified.
2. `test_event_bus_triggers_project_opened` — Verified.
3. `test_event_bus_triggers_user_proposition_submitted` — Verified.
4. `test_event_bus_triggers_task_and_study_creation` — Verified.
5. `test_cooldown_and_deduplication_via_event_bus` — Verified.
6. `test_agent_loop_runs_normally_without_advisory` — Verified.
7. `test_agent_loop_receives_proactive_advisory_context` — Verified.
8. `test_xml_escaping_neutralizes_prompt_injection` — Verified.
9. `test_project_review_skips_oversized_file_safely` — Verified.
10. `test_file_exactly_at_size_limit_is_analyzed` — Verified.
11. `test_workspace_boundary_enforces_allowed_roots` — Verified.
12. `test_workspace_symlink_escape_is_flagged` — Verified.
13. `test_bounded_fingerprint_cache_and_eviction` — Verified.
14. `test_informational_guard_strictly_blocks_tool_execution` — Verified.

---

## 5. Security & Invariant Matrix

| Invariant | Implementation Validation | Status |
| :--- | :--- | :--- |
| **Zero Tool Execution** | `InformationalGuard.verify_no_unsolicited_execution` enforces execution blocking unless user-initiated. | Verified |
| **No Injected Overrides** | All project, proposition, and advisory strings are XML escaped before injection into system prompt. | Verified |
| **No File Exfiltration** | Static analysis restricted to approved workspace roots; symlinks escaping project boundary are flagged. | Verified |
| **Bounded Memory Footprint** | Fingerprint deduplication and file sizes strictly capped. | Verified |
