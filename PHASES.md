# JARVIS Development Roadmap (Phases 0 — 13)

This document establishes the official 14-phase development lifecycle for JARVIS. 
**Advancement to any subsequent phase requires explicit human owner sign-off and safety audit verification.**

---

## Phase Overview Table

| Phase | Phase Name | Primary Objective | Safety Gatekeeper / Exit Criteria |
|---|---|---|---|
| **Phase 0** | **Architecture + Security** | Project structure, security specs, threat modeling, safe sandbox, mock suites | **COMPLETED & APPROVED** |
| **Phase 1** | **Safe JARVIS Core** | Core runtime, event bus, context manager, state machine, basic chat loop | **COMPLETED & APPROVED** |
| **Phase 2** | **Memory Subsystem** | Ephemeral context, encrypted SQLite/vector store, memory wipe/redact protocols | **COMPLETED (Hermetic tests pass 100%)** |
| **Phase 3** | **Tool Framework** | Typed tool registry, capability enforcement, HITL confirmation gatekeeper | **COMPLETED & VERIFIED (28 Phase 3 tests pass 100%)** |
| **Phase 4** | **Web & Research Engine** | Web search, URL reader, PDF/Markdown parsing, citation engine, SSRF/injection shields | **COMPLETED & VERIFIED (56 Phase 4 tests pass 100%, 150 total tests)** |
| **Phase 5** | **Voice Pipeline** | Offline wake-word ("Hey Jarvis"), local streaming STT, natural TTS synthesis | **COMPLETED & VERIFIED (16 Phase 5 tests pass 100%, 166 total tests)** |
| **Phase 6** | **Proactive Intelligence** | Autonomous project review, structured planning, coordinator, runtime wiring & resource hardening | **COMPLETED & VERIFIED (45 Phase 6 tests pass 100%, 211 total repository tests)** |
| **Phase 7** | **macOS Desktop Agent** | Tauri v2 shell, native accessibility bridges, scoped filesystem sandbox | **COMPLETED & VERIFIED (18 Phase 7 tests pass 100%, 229 total tests)** |
| **Phase 8** | **Android Client** | Kotlin / Jetpack Compose companion app, Android Keystore, local network transport, hardware pairing & production hardening | **COMPLETED & VERIFIED (47 Phase 8 tests pass 100%, 277 total tests)** |
| **Phase 9** | **Integrations Framework** | Sandboxed connectors for Gmail, Google Calendar, Google Drive, Slack, GitHub | **COMPLETED & VERIFIED (60 Phase 9 tests pass 100%, 337 total repository tests)** |
| **Phase 10** | **Security & Penetration Testing**| Comprehensive red-teaming, prompt injection fuzzing, privilege escalation tests | **COMPLETED & VERIFIED (18 Phase 10 tests pass 100%, 355 total repository tests)** |
| **Phase 11** | **Performance & Latency Tuning** | Sub-second latency optimization, token caching, memory footprint minimization | **COMPLETED & VERIFIED (16 Phase 11 tests pass 100%, 371 total repository tests)** |
| **Phase 12** | **Final Architectural Review** | End-to-end security audit, documentation sign-off, kill-switch verification | Formal owner verification of all privacy and fail-closed policies |
| **Phase 13** | **Production Deployment** | Local host installation, secure credential onboarding, service activation | **Final explicit human authorization to connect real accounts** |

---

## Detailed Phase Breakdown

### Phase 0 — Architecture + Security (CURRENT)
- **Scope**: Scaffold project structure, define threat model, author 10 architectural specification documents, implement mock sandbox, set up strict type checking and CI test suites.
- **Constraints**: Absolutely no real system hooks, no API tokens, no personal data, no daemons.
- **Deliverables**: `docs/`, `sandbox/`, `tests/`, `README.md`, `PHASES.md`.

### Phase 1 — Safe JARVIS Core
- **Scope**: Implement async event-driven runtime, dialogue state tracker, provider-agnostic model routing abstraction with mock fallback, and basic text conversation.
- **Constraints**: Local test runtime only; mock model provider only.

### Phase 2 — Memory Subsystem
- **Scope**: Implement 3-tier memory: short-term RAM, encrypted SQLite/SQLCipher episodic memory, and local vector embeddings. Add GDPR-style inspection and deletion CLI/API.
- **Constraints**: Synthetic memory fixtures only.

### Phase 3 — Tool Framework & Sandboxing
- **Scope**: Implement capability-based tool registry, permission evaluator (`LOCKED`, `NORMAL`, `SENSITIVE`), and interactive Human-In-The-Loop (HITL) cryptographic approval gatekeeper.
- **Constraints**: All tool executions remain bound to `sandbox/`.

### Phase 4 — Web & Research Engine
- **Scope**: Implement read-only web search, content scraping, semantic document parsing (PDF, Markdown), and citation extraction with prompt injection shields.
- **Constraints**: Outbound requests strictly filtered by domain whitelist and SSRF protections.

### Phase 5 — Voice Subsystem
- **Scope**: Build local audio pipeline: Porcupine/OpenWakeWord ("Hey Jarvis"), Whisper/Moonshine on-device STT, and Piper/Coqui/macOS AVFoundation TTS.
- **Constraints**: Audio processed locally in RAM; zero persistent audio logging.

### Phase 6 — Proactive Intelligence & Reasoning
- **Scope**: Autonomous project review routines, proactive recommendation engine, study/task plan generation, and polite epistemic disagreement engine.
- **Constraints**: Suggestions are purely informational; cannot trigger tool execution without user command.

### Phase 7 — macOS Desktop Agent [COMPLETED]
- **Scope**: Build Tauri v2 macOS application shell with Stitch-designed UI, system tray integration, keyboard shortcuts, and native AppleScript/Accessibility bridges.
- **Constraints**: User-specified folder access only; strict macOS entitlements; Unix Domain Socket (`0700`) JSON-RPC bridge; interactive HITL approval modal; purely informational proactive advisories.

### Phase 8 — Android Companion Client [COMPLETED]
- **Scope**: Develop native Kotlin Android client with Jetpack Compose UI, Android Keystore encryption, and secure local network sync.
- **Phase 8.1 Deliverables**: Project scaffolding, Gradle & AndroidX dependencies, JSON-RPC 2.0 DTO contracts, in-memory mock client, Keystore/Biometric security managers, Stitch Aether HUD mobile UI components, and automated test suite.
- **Phase 8.2 Deliverables**: Dedicated authenticated local network transport bridge (`NetworkBridgeServer`), hardware-backed asymmetric device pairing (`DevicePairingRegistry`), challenge-response authentication with 60s TTL and replay protection, and device revocation lifecycle.
- **Phase 8.3 Deliverables**: End-to-end live JARVIS session lifecycle, connection state machine (`DISCONNECTED` to `ERROR`), periodic authenticated heartbeat (`jarvis.heartbeat`), bounded exponential backoff auto-reconnect, request-response correlation, and fail-closed secret isolation.
- **Phase 8.4 Deliverables**: Production hardening, `SecureStorageManager` encrypted credential persistence and wipe paths, `FLAG_SECURE` window screenshot shielding, `network_security_config.xml` cleartext prohibition, socket timeouts & 5 MB payload bounds, stale approval rejection, and biometric HITL authorization.
- **Constraints**: End-to-end encrypted local pairing only. Informational-only proactive invariant strictly preserved on mobile. HITL authorization strictly enforced for sensitive tools across network boundaries. Direct Unix Domain Socket exposure prohibited.

### Phase 9 — Service Integrations [COMPLETED]
- **Scope**: Implement connectors for Gmail, Google Calendar, Google Drive, Slack, GitHub, Apple Notes, WhatsApp, and Telegram with dry-run preview capabilities.
- **Phase 9.1 Deliverables**: Service adapter foundation (`BaseServiceAdapter`), explicit capability contract (`ServiceCapability`), permission engine bridge (`ServicePermissionBridge`), credential provider isolation (`BaseCredentialProvider`), non-repudiable audit logging, fault isolation, hermetic mock messaging adapter, and IPC/Network service endpoints.
- **Phase 9.2 Deliverables**: Specific hermetic connectors (`GmailConnector`, `GoogleCalendarConnector`, `GoogleDriveConnector`, `SlackConnector`, `GitHubConnector`), explicit capability manifests, simulation hooks for failure modes (rate-limiting, outage, timeout, auth failure), single-use `ApprovalToken` HITL gating for write/send/delete operations, and credential non-disclosure across all subsystems.
- **Phase 9.3 Deliverables**: Real service authentication architecture, OS-secure storage (`KeychainSecureStorage`, `InMemorySecureStorage`), typed credential models (`OAuth2Credentials`, `ApiTokenCredentials`, `BotTokenCredentials`), `OAuth2LifecycleManager` with single-use 256-bit CSRF state protection, token expiration calculation and refresh lifecycle, service auth adapters (`GmailAuthAdapter`, `GoogleCalendarAuthAdapter`, `GoogleDriveAuthAdapter`, `SlackAuthAdapter`, `GitHubAuthAdapter`), and network safety disabled by default (`SystemConfig.enable_external_services = False`).
- **Phase 9.4 Deliverables**: Common secure HTTP transport (`SecureHttpTransport`, `MockHttpTransport`), centralized execution gate (`ServiceExecutionManager`), mutation duplicate protection and idempotency caching (`IdempotencyManager`), bounded exponential backoff & jitter for idempotent calls, HTTPS-only scheme validation, 5 MB request/response limits, concurrency limits (`Semaphore(10)`), fail-closed emergency stop integration, and zero secret leakage.
- **Constraints**: Read-only first; all write/send/delete actions permanently gated behind interactive confirmation. Sensitive capabilities (`SEND`, `DELETE`, `EXECUTE`, `CREATE`, `UPDATE`) strictly require HITL `ApprovalCard` + single-use `ApprovalToken`. Plaintext credentials prohibited in logs, IPC, or metadata. Zero external network dependencies in tests.

### Phase 10 — Security & Penetration Testing [COMPLETED]
- **Scope**: Adversarial red-teaming: direct/indirect prompt injection fuzzing, privilege escalation attempts, secret exfiltration attacks, and fail-closed audit.
- **Deliverables**: Adversarial prompt fuzzer (`AdversarialPromptFuzzer`), privilege escalation penetration tester (`PrivilegeEscalationTester`), cryptographic audit chain integrity verifier (`AuditIntegrityVerifier`), security vulnerability scanner (`SecurityVulnerabilityScanner`), automated red-team test suite, ADR-026, zero high/critical vulnerabilities verified.
- **Constraints**: Read-only first; all write/send/delete actions permanently gated behind interactive confirmation. Zero secrets stored in repository. Automated verification of fail-closed invariants.

### Phase 11 — Performance Optimization [COMPLETED]
- **Scope**: Token optimization, KV-cache acceleration, local quantized model execution (GGUF via llama.cpp/vLLM), sub-second latency optimization, memory footprint minimization, and resource benchmarking.
- **Deliverables**: Token context optimizer (`TokenOptimizer`), semantic response cache (`SemanticResponseCache`), local quantized model provider (`LocalQuantizedProvider`), performance benchmarker (`PerformanceBenchmarker`), process memory guard (`MemoryGuard`), automated test suite, ADR-027, TTFT < 400ms SLA verified, and RAM footprint strictly < 2GB.
- **Constraints**: Hermetic execution in tests; zero persistent prompt leak in cache across security sessions; proactive garbage collection and memory compaction triggered at 1536 MB.

### Phase 12 — Final Review & Verification
- **Scope**: Complete holistic audit of security policies, kill-switch behavior, error handling, and privacy compliance.

### Phase 13 — Installation & Deployment
- **Scope**: Provision encrypted local vault, initialize user credentials in OS Keychain, configure local launchd daemon (if permitted), and perform first-time live pairing.
