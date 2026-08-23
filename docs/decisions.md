# JARVIS Architecture Decision Records (ADRs)

> **Phase 0 — Safe Development Specification**

This document records the foundational architectural decisions, trade-off analyses, and technology selections made for **JARVIS**.

---

## Index of Decisions

- [ADR-001: Core Daemon Runtime Language](#adr-001-core-daemon-runtime-language)
- [ADR-002: Desktop Client Shell Framework](#adr-002-desktop-client-shell-framework)
- [ADR-003: Android Companion Client Stack](#adr-003-android-companion-client-stack)
- [ADR-004: Local Storage, Memory & Cryptographic Engine](#adr-004-local-storage-memory--cryptographic-engine)
- [ADR-005: Provider-Agnostic Model Routing Abstraction](#adr-005-provider-agnostic-model-routing-abstraction)
- [ADR-006: Human-In-The-Loop (HITL) Gatekeeper Architecture](#adr-006-human-in-the-loop-hitl-gatekeeper-architecture)
- [ADR-007: Inter-Process Communication (IPC) Protocol](#adr-007-inter-process-communication-ipc-protocol)
- [ADR-008: Standard AES-256-GCM AEAD Field-Level Encryption and Inverted Index](#adr-008-standard-aes-256-gcm-aead-field-level-encryption-and-inverted-index)
- [ADR-009: Typed Tool Registry, Process-Isolated Execution Sandbox, and Cryptographic Approval Tokens](#adr-009-typed-tool-registry-process-isolated-execution-sandbox-and-cryptographic-approval-tokens)
- [ADR-010: Secure Web Research Foundation, SSRF Defense, and Untrusted Web Content Isolation](#adr-010-secure-web-research-foundation-ssrf-defense-and-untrusted-web-content-isolation)
- [ADR-011: Typed Search Provider Abstraction and Per-Result Security Filtering](#adr-011-typed-search-provider-abstraction-and-per-result-security-filtering)
- [ADR-012: Secure Document Parsing (PDF/Markdown), Text Normalization, and Verifiable Citation Engine](#adr-012-secure-document-parsing-pdfmarkdown-text-normalization-and-verifiable-citation-engine)
- [ADR-013: Local-Only Offline Voice Subsystem and Ephemeral Audio Buffer Architecture](#adr-013-local-only-offline-voice-subsystem-and-ephemeral-audio-buffer-architecture)
- [ADR-014: Proactive Intelligence, Autonomous Project Review Routines, and Informational-Only Safety Guard](#adr-014-proactive-intelligence-autonomous-project-review-routines-and-informational-only-safety-guard)
- [ADR-015: Proactive Intelligence Coordinator, Rate-Limited Event Triggers, and Dialogue Advisory Architecture](#adr-015-proactive-intelligence-coordinator-rate-limited-event-triggers-and-dialogue-advisory-architecture)

---

### ADR-015: Proactive Intelligence Coordinator, Rate-Limited Event Triggers, and Dialogue Advisory Architecture
- **Status**: Accepted
- **Context**: Disconnected proactive features risk triggering uncoordinated checks, spamming the user with duplicate recommendations, causing performance degradation during background scans, or injecting raw unvalidated context into LLM dialogue turns.
- **Decision**: Implement a **Centralized Proactive Intelligence Coordinator (`ProactiveCoordinator`)** with event-driven triggers (`ProactiveTrigger`), **Rate-Limiting Cooldown Windows** per trigger type, **Deterministic SHA-256 Suggestion Deduplication**, and a **Non-Invasive Dialogue Advisory Layer (`ProactiveDialogueAdvisor`)** emitting inert XML data structures (`<proactive_advisory>`).
- **Rationale**:
  1. Prevents notification fatigue and recommendation thrashing by deduplicating repeated findings and enforcing cooldown limits.
  2. Protects conversational context from prompt injection by wrapping project review findings and user propositions inside inert XML tags.
  3. Preserves human-in-the-loop boundaries: proactive coordinator advice is structured as system/user observations without granting autonomous execution capabilities.
  4. Provides complete observability through tamper-evident SHA-256 chained audit logs.
- **Consequences**: Proactive triggers are rate-limited; urgent out-of-band evaluations must explicitly use `force=True` or `MANUAL_REQUEST`.


---

### ADR-014: Proactive Intelligence, Autonomous Project Review Routines, and Informational-Only Safety Guard
- **Status**: Accepted
- **Context**: Autonomous AI proactivity (recommending actions, analyzing projects, generating study plans, identifying code smells) risks triggering unrequested side effects, unexpected tool executions, or unauthorized file/network modifications.
- **Decision**: Implement a **Strictly Informational Proactive Intelligence Architecture** featuring autonomous static project reviews (`ProjectReviewEngine`), structured study and task plan generation (`PlanGenerator`), polite epistemic disagreement analysis (`ReasoningAnalyzer`), and an **Informational-Only Guard (`InformationalGuard`)**.
- **Rationale**:
  1. Guarantees zero unsolicited tool execution: proactive suggestions, review findings, and plans are explicitly marked as non-executable (`is_informational_only=True`, `is_executable_directly=False`).
  2. Protects codebase integrity: project reviews are strictly read-only and generate health scores without modifying source files.
  3. Promotes epistemic honesty: politely challenges flawed user premises (e.g. bypassing confirmation gates, storing plaintext passwords) while providing constructive alternatives.
  4. Preserves human sovereignty: all actions resulting from proactive recommendations require explicit, interactive user commands.
- **Consequences**: Applying or executing recommendations generated by the proactive engine requires subsequent explicit user command turns.


---

### ADR-013: Local-Only Offline Voice Subsystem and Ephemeral Audio Buffer Architecture
- **Status**: Accepted
- **Context**: Voice interaction presents severe privacy risks: continuous ambient microphone recording, unencrypted cloud speech transmission, permanent audio file accumulation on disk, and indirect prompt injection through acoustic channels.
- **Decision**: Implement a **Local-Only, Privacy-First Voice Pipeline** with offline wake-word spotting (`BaseWakeWordDetector`), on-device streaming speech-to-text (`BaseSTTProvider`), local text-to-speech synthesis (`BaseTTSProvider`), bounded in-memory FIFO ring buffers (`AudioRingBuffer`, 5 MB max), **Zero Disk Audio Persistence**, **Untrusted Speech Sanitization (`InputSanitizer`)**, and **Audit Logging Without Raw Audio**.
- **Rationale**:
  1. Prevents eavesdropping and unauthorized recording by keeping all raw audio frames ephemerally in RAM and immediately wiping them upon turn completion.
  2. Eliminates cloud surveillance and network exfiltration risks by ensuring zero audio bytes leave the local device.
  3. Neutralizes adversarial speech prompt injection attacks before reaching LLM reasoning or tool execution.
  4. Enforces non-repudiable audit logging while strictly omitting audio waveforms from audit records.
- **Consequences**: Real-time voice processing requires local CPU/Metal compute resources rather than offloading to high-latency external cloud speech APIs.


---

### ADR-012: Secure Document Parsing (PDF/Markdown), Text Normalization, and Verifiable Citation Engine
- **Status**: Accepted
- **Context**: Document files (PDFs, Markdown) present major attack surfaces: decompression/zip bombs, embedded JavaScript action exploits (`/JS`, `/Launch`), malicious inline HTML, arbitrary path traversals outside the sandbox, and indirect prompt injection.
- **Decision**: Implement a **Pure-Python Secure Document Parser Engine** with strict stream decompression limits (10 MB per stream, 50 MB total), active exploit neutralization, inline HTML sanitization, Unicode NFKC text normalization, **Verifiable Citation Tracking (`CitationManager`)** with SHA-256 fingerprinting, and **Untrusted XML Isolation Wrapping (`<untrusted_document_content>`)**.
- **Rationale**:
  1. Prevents remote code execution, memory exhaustion, and binary parser vulnerabilities by avoiding external C/C++ binary wrappers.
  2. Guarantees non-repudiable factual citations anchored to specific pages, sections, and source document hashes.
  3. Neutralizes indirect prompt injection attacks embedded inside user documents by encapsulating extracted text in inert XML data delimiters.
- **Consequences**: Complex non-standard vector drawing operations or encrypted proprietary PDF formats require converting to standard formats prior to parsing.


---

### ADR-011: Typed Search Provider Abstraction and Per-Result Security Filtering
- **Status**: Accepted
- **Context**: Search engines can return malicious URLs (file paths, intranet IP addresses, cloud metadata endpoints), prompt injection attacks in snippets, or oversized response payloads.
- **Decision**: Implement a **Provider-Agnostic Search Architecture (`BaseSearchProvider`)** with input query length limits (500 chars), result count clamping (1-10), **Per-Result URL & SSRF Validation Filtering** dropping private/loopback/metadata destinations, and **Untrusted XML Isolation Wrapping (`<untrusted_search_results>`)**.
- **Rationale**:
  1. Prevents poisoned search index attacks from reaching internal infrastructure or triggering local file disclosure.
  2. Ensures consistent ranking, schema typing, and domain extraction across different search backends.
  3. Eliminates prompt injection vectors in search results by isolating snippet text from agent instructions.
- **Consequences**: Adding new live search backends requires implementing `BaseSearchProvider` and conforming to standardized `SearchResultItem` schemas.


---

### ADR-001: Core Daemon Runtime Language
- **Status**: Accepted
- **Context**: The core daemon orchestrates AI models, parses complex documents, manages vector memory, executes tools, and coordinates cross-platform IPC. We evaluated Python 3.12+, Rust, and Go.
- **Decision**: Choose **Python 3.12+** with strict type enforcement (`mypy --strict`, Pydantic v2).
- **Rationale**:
  1. Python has the richest, most up-to-date ecosystem for AI/ML tooling, local inference bindings (llama.cpp, ONNX Runtime, Whisper), and document parsing.
  2. With Python 3.12, asyncio improvements, sub-interpreter support, and static typing, Python delivers the required responsiveness and maintainability.
  3. Faster iteration and easier extensibility for custom agent tools.
- **Consequences**: Strict type checking and linting must be enforced in CI to maintain production reliability.

---

### ADR-002: Desktop Client Shell Framework
- **Status**: Accepted
- **Context**: The macOS desktop interface requires a lightweight floating HUD, system tray residency, global keyboard shortcuts, and a rich UI without excessive RAM consumption. We evaluated Tauri v2, Electron, and pure Native Swift.
- **Decision**: Choose **Tauri v2 (Rust backend + Webview frontend)** with a native Swift bridge for macOS Accessibility APIs.
- **Rationale**:
  1. Electron consumes 200MB–500MB RAM at idle; Tauri v2 consumes <30MB RAM.
  2. Tauri's Rust core provides native memory safety and capability-based security permissions for frontend-backend IPC.
  3. Webview frontend allows using modern, highly polished web UI design patterns (and compatibility with Stitch MCP design tools).
- **Consequences**: Requires Rust toolchain for compiling the desktop shell.

---

### ADR-003: Android Companion Client Stack
- **Status**: Accepted
- **Context**: The mobile companion requires seamless integration with Android Keystore (StrongBox), background WorkManager sync, biometric authentication, and a responsive UI. We evaluated Kotlin + Jetpack Compose, React Native, and Flutter.
- **Decision**: Choose **Kotlin + Jetpack Compose (Native Android)**.
- **Rationale**:
  1. Direct, zero-overhead access to native Android security APIs (BiometricPrompt, Android Keystore, NotificationListenerService).
  2. Optimal battery performance and background sync reliability via Jetpack WorkManager.
  3. Zero cross-platform framework overhead or bridging vulnerabilities.
- **Consequences**: Mobile codebase remains distinct from desktop web UI, but shares identical data contracts and mTLS protocol.

---

### ADR-004: Local Storage, Memory & Cryptographic Engine
- **Status**: Accepted
- **Context**: JARVIS requires fast structured query capabilities, relational memory linking, vector similarity search, and zero-compromise encryption at rest without requiring a running database server.
- **Decision**: Choose **SQLite with SQLCipher (AES-256-GCM)** paired with **Qdrant Embedded / SQLite-VSS** for local vector indexing.
- **Rationale**:
  1. Serverless, single-file storage with rock-solid ACID reliability.
  2. SQLCipher provides transparent page-level AES-256 encryption at rest.
  3. Embedded vector search runs locally on CPU with zero network dependency.
- **Consequences**: Encryption keys must be securely retrieved from the OS Keychain at runtime.

---

### ADR-005: Provider-Agnostic Model Routing Abstraction
- **Status**: Accepted
- **Context**: Tying JARVIS to a single cloud provider (e.g. OpenAI or Anthropic) introduces vendor lock-in, privacy risks, and single-point-of-failure issues.
- **Decision**: Implement a **3-Tier Model Router (`FastTier`, `ReasoningTier`, `LocalPrivateTier`)** with fallback support.
- **Rationale**:
  1. Allows dynamic routing based on task sensitivity: private documents and credentials route to offline local models (Ollama / Llama.cpp), while complex multi-step coding routes to high-reasoning models.
  2. Automatic failover to local models if internet connectivity is lost.
  3. Standardized Pydantic schemas decouple prompt logic from vendor-specific API structures.
- **Consequences**: Requires maintaining prompt compatibility across different model architectures.

---

### ADR-006: Human-In-The-Loop (HITL) Gatekeeper Architecture
- **Status**: Accepted
- **Context**: Autonomous AI agents can hallucinate or be tricked into executing destructive, irreversible, or communicating actions.
- **Decision**: Enforce a **Deterministic Cryptographic Approval Gatekeeper** for all `SENSITIVE`, `DESTRUCTIVE`, and `IRREVERSIBLE` actions.
- **Rationale**:
  1. The LLM cannot authorize itself; authority resides exclusively with the human owner.
  2. Generates a human-readable dry-run modal with diffs and parameters.
  3. Single-use cryptographic tokens expire in 60s to prevent replay attacks.
- **Consequences**: Sensitive actions require user interaction, prioritizing safety over full autonomy.

---

### ADR-007: Inter-Process Communication (IPC) Protocol
- **Status**: Accepted
- **Context**: The desktop UI, mobile companion, and CLI must communicate with the core daemon efficiently and securely on the local machine.
- **Decision**: Choose **Unix Domain Sockets (UDS) with JSON-RPC / gRPC** for local IPC, and **mTLS with Noise Protocol** for cross-device network sync.
- **Rationale**:
  1. Unix Domain Sockets avoid opening network ports on `localhost`, eliminating port-scanning and cross-origin browser attacks (DNS rebinding / CSRF).
  2. OS-level file permissions (`0700`) ensure only the active user can connect to the socket.
- **Consequences**: Native socket handling implemented in Tauri Rust backend and Python daemon.

---

### ADR-008: Standard AES-256-GCM AEAD Field-Level Encryption and Inverted Index
- **Status**: Accepted (Security Reviewed)
- **Context**: Phase 2 requires persistent memory with zero plaintext sensitive data on disk, strict consent boundaries, high performance (<2ms retrieval), and standard, peer-reviewed cryptographic primitives.
- **Decision**: Implement **Standard AES-256-GCM AEAD (NIST SP 800-38D)** backed by OpenSSL / libcrypto with **Authenticated Associated Data (AAD)** binding memory metadata, paired with an **In-Memory Inverted Keyword Index** and modular **EmbeddingProvider/VectorIndex** interfaces.
- **Rationale**:
  1. Uses standard, peer-reviewed NIST SP 800-38D AEAD construction rather than any homemade cipher or keystream.
  2. Guarantees confidentiality and tampering rejection (`TamperedCiphertextError`) for sensitive memory fields and bound metadata on disk.
  3. Provides sub-millisecond retrieval (<0.1ms) while decoupling storage from future vector database backends (Qdrant/SQLite-VSS).
- **Consequences**: Key provider interface cleanly abstracts test sandbox keys from future hardware-backed OS Keychain storage.

---

### ADR-009: Typed Tool Registry, Process-Isolated Execution Sandbox, and Cryptographic Approval Tokens
- **Status**: Accepted
- **Context**: The LLM must be strictly prohibited from executing arbitrary shell, filesystem, or network commands. All tool executions must be typed, validated, isolated, bounded by timeouts, and sensitive side-effects must require human consent.
- **Decision**: Implement a **Central Typed Tool Registry** with strict parameter schema validation (disallowing extra properties), a **ProcessSandboxExecutor** with scrubbed environment variables and timeout/size enforcement, **Single-Use Cryptographic Approval Tokens** binding parameters, session, and tool ID via SHA-256 hashes, and **Untrusted XML Tag Isolation (`<untrusted_tool_output>`)** for prompt injection defense.
- **Rationale**:
  1. Prevents arbitrary command execution, code execution, and shell injection vulnerabilities.
  2. Eliminates secret and credential leakage into tool subprocesses by wiping host environment variables.
  3. Prevents approval token replay, parameter tampering, session hijacking, or cross-tool authorization confusion.
  4. Neutralizes indirect prompt injection attacks by formatting tool output as untrusted structured data.
- **Consequences**: Adding new capabilities requires defining explicit Pydantic schemas, permissions, risk levels, and sandbox boundaries.

---

### ADR-010: Secure Web Research Foundation, SSRF Defense, and Untrusted Web Content Isolation
- **Status**: Accepted
- **Context**: Autonomous web browsing can expose the agent and host system to SSRF attacks (accessing internal IP addresses, cloud metadata services `169.254.169.254`, loopback interfaces), DNS rebinding, infinite redirect loops, oversized payload memory attacks, and indirect prompt injection.
- **Decision**: Implement a multi-layered **Secure Web Research Engine** featuring strict URL scheme whitelisting (`http`/`https` only), credential userinfo rejection, comprehensive IPv4/IPv6 private & metadata SSRF denylisting with DNS resolution validation, step-by-step redirect inspection (max 3 hops), streaming payload size enforcement (512 KB cap), HTML-to-Markdown normalization with script/style stripping, and untrusted XML content encapsulation (`<untrusted_web_content>`).
- **Rationale**:
  1. Prevents exfiltration of local network services, AWS/GCP/Azure instance metadata, and container infrastructure.
  2. Protects host memory and resources against payload flooding and hanging network streams.
  3. Eliminates indirect prompt injection attacks by parsing HTML into inert text and tagging it as untrusted data.
- **Consequences**: Outbound research requests are strictly read-only and bounded; arbitrary socket connections or unverified protocols remain blocked.

