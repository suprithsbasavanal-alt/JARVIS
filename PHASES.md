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
| **Phase 3** | **Tool Framework** | Typed tool registry, capability enforcement, HITL confirmation gatekeeper | **Requires Human Authorization** |
| **Phase 4** | **Web & Research Engine** | Sandboxed web search, URL reader, summarizer, citation graph generator | Indirect prompt injection & SSRF defense suite verified |
| **Phase 5** | **Voice Pipeline** | Offline wake-word ("Hey Jarvis"), local streaming STT, natural TTS synthesis | Zero continuous audio transmission to cloud; offline wake test pass |
| **Phase 6** | **Proactive Intelligence** | Background ideation, task planning, project recommendations, polite disagreement | Proactivity bounded; zero unsolicited destructive action execution |
| **Phase 7** | **macOS Desktop Agent** | Tauri v2 shell, native accessibility bridges, scoped filesystem sandbox | OS permission prompts scoped to explicit user directories |
| **Phase 8** | **Android Client** | Kotlin / Jetpack Compose companion app, Android Keystore, local notification bridge | Zero-trust mTLS / E2EE device pairing & authentication verified |
| **Phase 9** | **Integrations Framework** | Sandboxed connectors for Gmail, Google/Apple Calendar, WhatsApp, Telegram | Granular OAuth scopes; explicit confirmation required for message sending |
| **Phase 10** | **Security & Penetration Testing**| Comprehensive red-teaming, prompt injection fuzzing, privilege escalation tests | Zero high/critical vulnerabilities; audit logging non-repudiable |
| **Phase 11** | **Performance & Latency Tuning** | Sub-second latency optimization, token caching, memory footprint minimization | Local inference latency < 400ms TTFT; RAM footprint < 2GB |
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

### Phase 7 — macOS Desktop Agent
- **Scope**: Build Tauri v2 macOS application shell with Stitch-designed UI, system tray integration, keyboard shortcuts, and native AppleScript/Accessibility bridges.
- **Constraints**: User-specified folder access only; strict macOS entitlements.

### Phase 8 — Android Companion Client
- **Scope**: Develop native Kotlin Android client with Jetpack Compose UI, Android Keystore encryption, and secure local network sync.
- **Constraints**: End-to-end encrypted local pairing only.

### Phase 9 — Service Integrations
- **Scope**: Implement connectors for Gmail, Google Calendar, Apple Calendar, WhatsApp, Telegram, and Apple Notes with dry-run preview capabilities.
- **Constraints**: Read-only first; all write/send actions permanently gated behind interactive confirmation.

### Phase 10 — Security & Penetration Testing
- **Scope**: Adversarial red-teaming: direct/indirect prompt injection fuzzing, privilege escalation attempts, secret exfiltration attacks, and fail-closed audit.

### Phase 11 — Performance Optimization
- **Scope**: Token optimization, KV-cache acceleration, local quantized model execution (GGUF via llama.cpp/vLLM), and resource benchmarking.

### Phase 12 — Final Review & Verification
- **Scope**: Complete holistic audit of security policies, kill-switch behavior, error handling, and privacy compliance.

### Phase 13 — Installation & Deployment
- **Scope**: Provision encrypted local vault, initialize user credentials in OS Keychain, configure local launchd daemon (if permitted), and perform first-time live pairing.
