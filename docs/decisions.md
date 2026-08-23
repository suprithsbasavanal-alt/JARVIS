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

---

### ADR-011: Pure-Python Document Parsing, Resource Sandboxing, and Citation Preservation
- **Status**: Accepted
- **Context**: Autonomous processing of user-provided PDF and Markdown research documents creates risks of indirect prompt injection, memory exhaustion from decompression bombs, arbitrary filesystem path traversal, and fabricated citations.
- **Decision**: Implement a **Pure-Python PDF & Markdown Parser** with streaming page-by-page tokenization, document size enforcement (10 MB PDF, 2 MB Markdown), extraction timeouts (5s), untrusted XML encapsulation (`<untrusted_document_content>`), and deterministic citation preservation.
- **Rationale**:
  1. Prevents host binary vulnerabilities associated with heavy C++ PDF rendering engines.
  2. Protects against memory exhaustion and infinite loops during PDF stream parsing.
  3. Guarantees that document text cannot break prompt boundary delimiters or execute hidden prompt injection directives.
- **Consequences**: Complex multi-column OCR requires downstream OCR plugins; standard textual PDFs and Markdown parse with zero binary dependencies.

---

### ADR-012: Local Streaming Voice Pipeline with Ephemeral Audio Memory
- **Status**: Accepted
- **Context**: Voice interaction requires low-latency offline wake-word activation, speech-to-text, and speech synthesis without transmitting audio frames over external networks or creating persistent audio surveillance recordings on disk.
- **Decision**: Implement an **Offline Streaming Voice Engine** with modular provider interfaces (`LocalWakeWordDetector`, `LocalSTTProvider`, `LocalTTSProvider`), an ephemeral in-memory ring buffer (10s max capacity) that zeroizes audio buffers upon transcription, and strict network prohibition.
- **Rationale**:
  1. Preserves privacy by guaranteeing microphone audio is never written to disk or transmitted over the network.
  2. Ephemeral ring buffer prevents memory growth and eliminates eavesdropping risks.
  3. Pluggable provider architecture enables drop-in integration with Whisper, Porcupine, Piper, or mock testing engines.
- **Consequences**: Audio transcription runs locally on CPU/Metal; system logs contain text transcripts only, never raw audio.

---

### ADR-013: Static Project Health Assessment & Informational Proactive Recommendations
- **Status**: Accepted
- **Context**: Autonomous code reviews and proactive assistance must assist developers without triggering unauthorized file modifications, unexpected git commits, or unprompted tool actions.
- **Decision**: Implement `ProjectReviewEngine` with deterministic regex heuristics, structural health scoring (0–100), and `InformationalGuard` that strictly disallows unsolicited tool execution.
- **Rationale**:
  1. Provides objective, instant static health metrics across security, testing, architecture, and code quality.
  2. Ensures proactive suggestions are purely informational advisory signals requiring explicit user initiation to execute.
- **Consequences**: Static analysis is fast and deterministic; complex inter-procedural taint tracking defers to dedicated SAST tools.

---

### ADR-014: Epistemic Reasoning & Polite Disagreement Engine
- **Status**: Accepted
- **Context**: When users propose insecure, flawed, or destructive configurations (e.g., storing plaintext credentials, disabling approval gates, deleting databases without backup), the AI must not passively execute dangerous requests.
- **Decision**: Implement `ReasoningAnalyzer` to evaluate user propositions against safety principles and generate polite, constructive counter-arguments with safer alternative solutions.
- **Rationale**:
  1. Protects the user and environment against catastrophic misconfigurations.
  2. Maintains a respectful, constructive collaborative tone while upholding safety boundaries.
- **Consequences**: Epistemic checks occur prior to execution, preventing unsafe actions before confirmation cards are generated.

---

### ADR-015: Centralized Proactive Intelligence Coordination and Rate Limiting
- **Status**: Accepted
- **Context**: Multiple proactive triggers (session startup, project opening, epistemic checks, periodic reviews) can flood the user or dialogue context with redundant suggestions.
- **Decision**: Implement `ProactiveCoordinator` with per-trigger cooldowns, priority threshold filtering, and SHA-256 fingerprint deduplication.
- **Rationale**:
  1. Prevents notification spam and cognitive overload.
  2. Guarantees deterministic evaluation lifecycle with SHA-256 chained audit logs.
- **Consequences**: Triggers occurring within cooldown windows are safely suppressed without disrupting runtime execution.

---

### ADR-016: Proactive Runtime Wiring, XML Context Sanitization, and Bounded Resource Isolation
- **Status**: Accepted
- **Context**: Connecting proactive intelligence to the live `EventBus` and `AgentLoop` requires guarantees against event bus blockage, prompt injection breakout, directory traversal, memory leaks, and unbounded file processing.
- **Decision**: Implement `ProactiveRuntimeBridge` for asynchronous domain event subscription, enforce **XML entity escaping (`xml.sax.saxutils.escape`)** across all proactive data blocks, implement **per-file size limits (5 MB)** and **workspace root validation (`allowed_roots`)** in `ProjectReviewEngine`, and use a **bounded LRU cache (`OrderedDict`, capacity 1,000)** for suggestion fingerprints.
- **Rationale**:
  1. Asynchronous event subscription decouples background observation from critical dialogue turns.
  2. XML character entity escaping neutralizes malicious attempts to break out of `<proactive_advisory>` system tags.
  3. Strict file size and workspace boundaries prevent denial-of-service and filesystem traversal during project reviews.
  4. Bounded fingerprint cache prevents memory leakage over long-running daemon sessions.
- **Consequences**: Proactive advisory context enters the agent's working context in Step 3 as inert informational data, with full security isolation.

---

### ADR-017: Tauri v2 Desktop Shell with Stitch-Designed Aether HUD and Unix Domain Socket JSON-RPC Bridge
- **Status**: Accepted
- **Context**: The macOS desktop client requires a native, low-latency, and memory-efficient user interface connecting to the Python core daemon while enforcing strict security isolation, least privilege, and non-repudiable auditability.
- **Decision**: Use a **Tauri v2** desktop host (Rust) managing native AppKit visual effects, system tray, and global shortcuts (`Cmd+Space` HUD, `Cmd+Shift+Esc` Emergency Stop), paired with a **Stitch-designed Aether HUD** frontend (HTML5/Vanilla TypeScript/CSS) and a **Unix Domain Socket (`0700` POSIX mode) / JSON-RPC 2.0** server with ephemeral auth token handshake.
- **Rationale**:
  1. *Resource Efficiency*: Tauri v2 leverages native WebKit with a lightweight footprint compared to heavy Electron shells.
  2. *Security Boundary*: Local Unix Domain Sockets with POSIX `0700` permissions prevent unauthorized cross-user access on the host system.
  3. *Least-Privilege Capabilities*: Tauri v2 ACL configuration restricts the webview from executing arbitrary shell commands or opening arbitrary network connections.
  4. *Human-in-the-Loop Integrity*: Sensitive actions generate interactive approval modals requiring explicit user authorization before single-use cryptographic tokens are dispatched.
  5. *Emergency Stop*: Native global hotkey (`Cmd+Shift+Esc`) immediately revokes active approval tokens and cancels in-flight agent operations.
- **Consequences**: Complete separation between the UI presentation layer and the Python core runtime, preserving all safety invariants from Phases 0–6.4.

---

### ADR-018: Android Companion Client Architecture, Hardware Security & Scaffolding
- **Status**: Accepted
- **Context**: The mobile companion requires a native, responsive UI capable of monitoring desktop agent health, submitting turns, confirming sensitive actions with biometric authentication, tracking study/task plans, and triggering emergency stops without compromising host daemon security or exposing unauthorized network attack surfaces.
- **Decision**: Implement a native **Kotlin & Jetpack Compose** companion client under `android/` structured with clean architecture (`data`, `security`, `ui`, `viewmodel`), **Android Keystore (StrongBox/AES-GCM-256)** for local token isolation, **AndroidX Biometric (`BiometricPrompt`)** hardware gating for sensitive HITL approvals, **Stitch Aether Mobile Theme** tokens, and typed **JSON-RPC 2.0 DTO contracts** backed by an in-memory mock client for Phase 8.1 bootstrap.
- **Rationale**:
  1. *Hardware Security*: Leveraging Android Keystore and BiometricPrompt guarantees that sensitive approvals cannot be triggered by background malware without physical user biometric presence.
  2. *Data Isolation*: Setting `allowBackup="false"` and configuring data extraction rules prevents cloud backup leaks of companion session credentials.
  3. *Informational Proactive Invariant*: Proactive DTOs carry `isInformationalOnly = true` and `isExecutableDirectly = false` to eliminate autonomous tool execution vectors on mobile.
  4. *Protocol Parity*: Kotlin data models exactly mirror the 10 JSON-RPC 2.0 methods established in `core/ipc_server.py`.
- **Consequences**: Provides a fully typed, secure, and testable Android codebase ready for subsequent local network bridge integration.

---

### ADR-019: Hardware-Backed Asymmetric Device Pairing & Local Network Transport Bridge
- **Status**: Accepted
- **Context**: Connecting the Android companion client over a local network (Wi-Fi/LAN) introduces risks of unauthorized device access, network eavesdropping, replay attacks, session hijacking, and direct exposure of the internal Unix Domain Socket.
- **Decision**: Implement a dedicated **Local Network Transport Bridge (`NetworkBridgeServer`)** and **Device Pairing Registry (`DevicePairingRegistry`)** enforcing:
  1. *Dedicated Network Bridge*: Do NOT expose the Unix Domain Socket directly to the network. Instead, run an authenticated TCP/TLS JSON-RPC 2.0 bridge that wraps calls with device session validation before proxying to `AgentLoop` and `PermissionEngine`.
  2. *Asymmetric Device Identity & Pairing*: Android generates an asymmetric key pair in `AndroidKeyStore`. Pairing requires desktop host confirmation of a 6-digit cryptographic pairing code (`jarvis.network.pair.begin` $\rightarrow$ `jarvis.network.pair.confirm`).
  3. *Mutual Challenge-Response Authentication*: Session creation requires solving a 32-byte CSPRNG challenge nonce signed by the device's hardware key (`jarvis.network.auth.challenge` $\rightarrow$ `jarvis.network.auth.verify`).
  4. *Replay & Expiration Defense*: Challenges expire in 60 seconds; consumed nonces are immediately tracked in `_consumed_nonces` and rejected if replayed.
  5. *Immediate Device Revocation*: Revoking a device immediately invalidates all active session tokens.
  6. *HITL Invariant Preservation*: Device authentication does NOT grant permission to execute sensitive tools; sensitive operations strictly require interactive `ApprovalCard` confirmation and single-use `ApprovalToken`.
- **Rationale**:
  1. Protects the desktop daemon against unauthorized local network devices.
  2. Guarantees that private keys never leave Android hardware keystore / TEE.
  3. Eliminates replay attacks, token forgery, and session hijacking.
  4. Preserves fail-closed HITL and Emergency Stop invariants across network boundaries.
- **Consequences**: Network transport is authenticated, encrypted, isolated, and non-repudiable with complete SHA-256 chained audit logs.

---

### ADR-020: Android ↔ macOS Secure Session Lifecycle, Connection State Machine & Live JARVIS Communication
- **Status**: Accepted
- **Context**: Real-time communication between the Android Companion Client and the JARVIS macOS daemon requires reliable connection lifecycle management, automated keepalive/heartbeat detection, bounded reconnection with exponential backoff, request-response correlation, and robust error handling without exposing host secrets, leaking private keys, or bypassing Human-in-the-Loop (HITL) authorization gates.
- **Decision**: Implement a **Strict Lifecycle Connection State Machine** and **Typed JSON-RPC 2.0 Live Communication Layer**:
  1. *Connection State Tracking*: Maintain explicit states (`DISCONNECTED`, `CONNECTING`, `AUTHENTICATING`, `CONNECTED`, `RECONNECTING`, `REVOKED`, `ERROR`) exposed via Kotlin `StateFlow<ConnectionState>`.
  2. *Periodic Authenticated Heartbeats*: Transmit `jarvis.heartbeat` every 15s to monitor connection health; transition to `RECONNECTING` upon socket loss or timeout.
  3. *Bounded Exponential Backoff*: Reconnection attempts follow exponential backoff (1s initial delay up to 30s max, 2.0x multiplier, max 5 attempts) and halt immediately upon device revocation or explicit user disconnect.
  4. *Request-Response Correlation & Payload Protection*: Match request and response identifiers (`response.id == request.id`), enforce strict 5 MB payload limits on incoming JSON-RPC lines to prevent DoS memory exhaustion, and handle JSON-RPC errors via typed `JsonRpcException` without exposing host daemon stack traces.
  5. *Preservation of Core Safety Invariants*:
     - **HITL Gate**: Network authentication does NOT grant permission to execute sensitive tools; sensitive operations require explicit interactive `ApprovalCard` approval and generate single-use `ApprovalToken`. Denial terminates execution.
     - **Emergency Stop**: Android companion can trigger `jarvis.system.emergency_stop` to immediately revoke all active approval tokens and cancel in-flight operations.
     - **Informational Proactive**: Proactive advisories carry `is_informational_only = true` and cannot trigger tool execution on Android or macOS.
     - **Secret Isolation**: Responses never transmit host daemon auth tokens, API keys, or private cryptographic material.
- **Rationale**:
  1. Prevents connection leaks, busy-loop thread exhaustion, and unhandled network drops.
  2. Guarantees that revoked companion devices cannot reconnect or access JARVIS core.
  3. Provides an end-to-end typed, reactive architecture from Android Jetpack Compose UI down to Python `AgentLoop`.
- **Consequences**: Android companion client functions reliably across local network disconnections while preserving all security invariants.

---

### ADR-021: Android Companion Production Hardening, Lifecycle Safety & Privacy Boundaries
- **Status**: Accepted
- **Context**: Moving the Android Companion Client to production readiness requires comprehensive defense-in-depth against Activity lifecycle leaks, background resource consumption, screen recording/task-switcher eavesdropping, stale approval execution, network timeouts, DoS memory exhaustion, and plaintext credential persistence.
- **Decision**: Implement a full suite of **Production Hardening, Lifecycle Safety, and Privacy Controls**:
  1. *Encrypted Credential Isolation (`SecureStorageManager`)*: Sensitive credentials and ephemeral session tokens are encrypted via Android Keystore (AES-GCM-256) and never stored in plaintext SharedPreferences, logs, or database records. Full credential zeroization (`wipeAllCredentials()`) executes on device revocation or explicit sign-out.
  2. *Window Security & Screenshot Shielding*: Enforce `FLAG_SECURE` on `MainActivity` window to block unauthorized screenshots, screen recording malware, and task-switcher snapshot leaks of confidential assistant conversations and approval cards.
  3. *Network Security Configuration & Cleartext Prohibition*: `network_security_config.xml` strictly enforces `cleartextTrafficPermitted="false"` across base configs and local domain definitions.
  4. *Socket Timeouts & Frame Bounds*: Configure 10s connection timeout, 15s socket read/write timeouts, and strict 5 MB message size limits to prevent connection hangs and payload memory exhaustion.
  5. *Concurrency & Pending Request Queue Bounding*: Throttle concurrent network requests via `Semaphore(10)` to prevent unbounded memory queuing.
  6. *Stale Approval Invalidation & Biometric Confirmation*: `MainViewModel` and `ApprovalDialog` validate card ID matching and prevent approving stale, expired, or non-existent requests. Sensitive actions strictly require biometric validation (`BiometricPrompt`) on supported hardware.
  7. *Local Fail-Closed Emergency Stop*: Invoking Emergency Stop immediately purges pending approval cards locally in UI state, clears in-flight operations, and notifies the host daemon.
  8. *Secret Scrubbing in Logs & Exceptions*: Automatically redact session tokens, hex keys, and credential strings from error messages, exceptions, and diagnostic logs.
- **Rationale**:
  1. Protects user privacy against mobile spyware, screen scrapers, and background log harvesters.
  2. Prevents stale approval race conditions and replay attacks across mobile lifecycles.
  3. Guarantees deterministic, memory-safe, and bounded resource utilization on Android devices.
- **Consequences**: Android client is fully production-hardened, private, fail-closed, and compliant with enterprise Android security standards.

---

### ADR-022: Secure Service Adapter Architecture, Capability Boundaries & Credential Isolation
- **Status**: Accepted
- **Context**: Enabling personal service integrations (Gmail, Calendar, WhatsApp, Telegram, Apple Notes) requires a modular, auditable, and capability-constrained connector architecture that prevents autonomous privilege escalation, credential leakage, undeclared capability access, and unbounded execution delays.
- **Decision**: Implement a **Centralized Service Registry with Capability-Enforced Adapters and Platform Credential Isolation**:
  1. *Typed Adapter & Capability Contract (`BaseServiceAdapter`)*: Every external connector implements explicit declared capabilities (`READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE`, `SEND`, `EXECUTE`). Requests for undeclared capabilities are rejected before dispatch.
  2. *HITL Permission Bridge (`ServicePermissionBridge`)*: Map capabilities to permission tiers. All state-modifying or outbound communication capabilities (`SEND`, `DELETE`, `CREATE`, `UPDATE`, `EXECUTE`) are classified as `SENSITIVE` and strictly require interactive Human-in-the-Loop (`ApprovalCard`) authorization and single-use `ApprovalToken` validation.
  3. *Credential Boundary (`BaseCredentialProvider`)*: Secrets (API keys, OAuth tokens, client secrets) are managed exclusively by credential providers, never stored in the registry or adapter metadata, and never exposed in `__repr__`, metadata dictionaries, IPC responses, or audit logs.
  4. *Non-Repudiable Chained Audit Logging*: Every service operation and administrative change generates a SHA-256 chained audit log entry with automated parameter secret sanitization (`[REDACTED]`).
  5. *Fault Isolation & Bounded Monitoring*: Asynchronous timeouts (15s execution, 3s health check) isolate external network degradation from blocking the core `AgentLoop`.
- **Rationale**:
  1. Guarantees that external services cannot be accessed without explicit permission and auditability.
  2. Prevents secret leakage across application layers and IPC bridges.
  3. Preserves fail-closed HITL and emergency-stop safety invariants across all personal service connectors.
- **Consequences**: External service ecosystem can scale to diverse third-party APIs while maintaining strict security and privacy boundaries.

---

### ADR-023: Specific Service Connectors, Hermetic Test Doubles & Capability Boundaries
- **Status**: Accepted
- **Context**: Phase 9.2 introduces specific connectors for email (Gmail), calendar (Google Calendar), cloud files (Google Drive), team messaging (Slack), and software repositories (GitHub). To maintain zero external network dependencies, avoid leaking production credentials, and guarantee strict test isolation, the architecture must support hermetic test doubles and simulated failure modes.
- **Decision**: Implement **Hermetic Connectors with Explicit Capability Manifests and Deterministic Simulation Hooks**:
  1. *Dedicated Adapters*: Create specialized adapter classes inheriting from `BaseHermeticConnector`: `GmailConnector`, `GoogleCalendarConnector`, `GoogleDriveConnector`, `SlackConnector`, and `GitHubConnector`.
  2. *Strict Capability Boundaries*: Each connector declares its supported capability subset. For example, `GmailConnector` declares `READ`, `SEARCH`, `CREATE`, `SEND`, `DELETE`. Operations requesting undeclared capabilities fail closed immediately with `UndeclaredCapabilityError`.
  3. *HITL Single-Use Token Enforcement*: Any state-modifying or outbound action (`send_email`, `post_message`, `create_event`, `upload_file`, `create_issue`, `delete_email`, `delete_file`) strictly requires an interactive `ApprovalCard` and single-use `ApprovalToken`. Token replay attempts are rejected.
  4. *Simulation Infrastructure (`ConnectorSimulationConfig`)*: Provide deterministic failure injection for rate-limiting (HTTP 429), outages (HTTP 503), timeouts, and authentication errors without performing live external network calls.
  5. *Credential Secrecy*: All connectors utilize `BaseCredentialProvider` and redact tokens/secrets from all metadata dictionaries, `__repr__`, IPC responses, and chained audit logs.
- **Rationale**:
  1. Ensures unit and integration tests run entirely hermetically, quickly, and deterministically without flake or external credential requirements.
  2. Prevents unauthorized or unintentional external actions through strict Human-in-the-Loop gating.
  3. Prepares a robust abstraction ready for real OAuth2 / credential onboarding in Phase 13.
- **Consequences**: Connectors are fully tested, fault-isolated, auditable, and secure against privilege escalation and token reuse.

---

### ADR-024: Secure Service Authentication, OAuth2 Lifecycle & Credential Isolation
- **Status**: Accepted
- **Context**: Enabling external services (Gmail, Google Calendar, Google Drive, Slack, GitHub) requires a production-ready authentication and credential management subsystem. The system must support OAuth 2.0 PKCE, API tokens, and Bot tokens with zero leakage in logs, exceptions, IPC responses, or audit records, while ensuring tests remain 100% hermetic and external network access is disabled by default.
- **Decision**: Implement a **Hardware-Backed Secure Credential Subsystem with OAuth2 Lifecycle Management and Network Disabling by Default**:
  1. *Typed Credential Models (`BaseCredential`)*: Define `OAuth2Credentials`, `ApiTokenCredentials`, `BotTokenCredentials`, and `GenericServiceCredentials` with custom `__repr__` outputting `[REDACTED]` and `to_safe_dict()` exposing zero secret tokens.
  2. *OS-Secure Storage Abstraction (`BaseSecureStorage`)*: Interface for OS Keychain (`KeychainSecureStorage`) and ephemeral memory storage (`InMemorySecureStorage`) with fail-closed security guarantees against plaintext disk leakage.
  3. *OAuth2 Lifecycle Manager (`OAuth2LifecycleManager`)*: Implements cryptographic 256-bit single-use CSRF state tokens with a 10-minute TTL, authorization URL generation, code exchange, token expiration calculation with a 60-second buffer, and safe refresh flows.
  4. *Atomic Rotation and Revocation*: Supports in-place credential rotation and full zeroization on connector revocation.
  5. *Network Disabled by Default*: `SystemConfig.enable_external_services` defaults to `False`, guaranteeing hermetic test execution and preventing unintentional network egress.
- **Rationale**:
  1. Prevents credential harvesting, shoulder surfing, and accidental token exposure across logs and IPC boundaries.
  2. Protects OAuth authentication against cross-site request forgery and authorization code reuse.
  3. Preserves deterministic unit testing without requiring real third-party developer accounts or internet connectivity.
- **Consequences**: Connectors operate securely with full credential lifecycle support and are prepared for user account onboarding in Phase 13.

---

### ADR-025: Controlled External Service Execution, Transport Isolation & Mutation Safety
- **Status**: Accepted
- **Context**: Executing live or simulated API requests against external third-party services (Gmail, Google Calendar, Google Drive, Slack, GitHub) poses risks of accidental duplicate mutation, denial-of-service via unbounded payload/memory consumption, credential leakage across logs and exceptions, cleartext network transport, and unauthorized actions bypassing Human-in-the-Loop gating.
- **Decision**: Implement a **Centralized Service Execution Gate with HTTPS Transport Isolation, Idempotency Guard, and Strict Invariant Enforcement**:
  1. *Central Execution Gateway (`ServiceExecutionManager`)*: All external operations must pass through `ServiceExecutionManager`. Enforces connector status, authentication validity, capability declaration, PermissionEngine / HITL gating, emergency stop, service revocation, and non-repudiable chained SHA-256 audit logging.
  2. *Idempotency & Duplicate Protection (`IdempotencyManager`)*: Tracks SHA-256 mutation fingerprints in an in-memory LRU cache with a 15-minute TTL. Concurrent duplicates fail with `DuplicateExecutionError`, and repeated requests return cached completed responses, preventing duplicate emails, messages, or issue creations.
  3. *Secure HTTP Transport (`SecureHttpTransport`)*: Enforces HTTPS-only URLs (rejects `http://`), 5 MB request and response limits, concurrency control via `asyncio.Semaphore(10)`, and bounded exponential backoff with jitter strictly for idempotent HTTP methods.
  4. *Automatic Header & Parameter Sanitization*: Automatically scrubs `Authorization`, `X-API-Key`, and `Cookie` headers from error traces, `HttpRequest.__repr__`, and audit records.
  5. *Fail-Closed Emergency Stop*: An active emergency stop immediately halts all external service execution without network egress.
- **Rationale**:
  1. Guarantees that external services cannot be contacted or mutated without passing full security and HITL authorization.
  2. Protects users against double-sends and unintended external state mutations during transient network failures.
  3. Prevents credential leaks in system diagnostics, error logs, and audit logs.
- **Consequences**: Complete external service integration lifecycle is hermetically tested, safely gated, observable, and ready for production operations.

---

### ADR-026: Adversarial Red-Teaming, Automated Fuzzing & Cryptographic Audit Verification
- **Status**: Accepted
- **Context**: Ensuring JARVIS is completely secure prior to performance tuning (Phase 11) and deployment (Phase 13) requires formal validation against prompt injection, privilege escalation, secret exfiltration, path traversal, and audit tampering vectors.
- **Decision**: Implement a **Dedicated Security & Red-Teaming Suite (`security/redteam/`)**:
  1. *Adversarial Prompt Fuzzing (`AdversarialPromptFuzzer`)*: Automated testing of direct jailbreaks, DAN personas, permission tier bypasses, boundary tag breakouts, base64 obfuscation, and markdown exfiltration.
  2. *Privilege Escalation Analysis (`PrivilegeEscalationTester`)*: Verification that `LOCKED` mode prohibits tool execution, `SENSITIVE` operations fail closed without single-use `ApprovalToken`, and parameter tampering or token replay are strictly rejected.
  3. *Audit Chain Integrity Verifier (`AuditIntegrityVerifier`)*: Mathematical validation of SHA-256 append-only audit chains with active simulation of record deletions, payload modifications, and sequence reordering.
  4. *Static & Runtime Security Scanner (`SecurityVulnerabilityScanner`)*: Automated inspection for leaked credentials, private subnet SSRF targets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`, `169.254.169.254`), and cleartext HTTP endpoints.
- **Rationale**:
  1. Provides verifiable, non-repudiable proof that zero critical/high security vulnerabilities exist across the system.
  2. Protects the owner against LLM prompt manipulation, unauthorized file access, and side-channel exfiltration attacks.
  3. Guarantees the integrity of the tamper-evident audit trail for post-incident analysis.
- **Consequences**: Platform security is rigorously verified with automated regression testing in CI.






