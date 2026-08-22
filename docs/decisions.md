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

### ADR-008: Authenticated Field-Level Encryption and Inverted Index for Memory
- **Status**: Accepted
- **Context**: Phase 2 requires persistent memory with zero plaintext sensitive data on disk, strict consent boundaries, high performance (<2ms retrieval), and zero mandatory external C-extensions or heavy vector engine downloads in the development sandbox.
- **Decision**: Implement **Application-Level Authenticated Encryption (Encrypt-then-MAC with HMAC-SHA256 and key separation)** on SQLite, paired with an **In-Memory Inverted Keyword Index** and modular **EmbeddingProvider/VectorIndex** interfaces.
- **Rationale**:
  1. Allows hermetic execution without requiring compiled SQLCipher binaries or external vector databases during core sandbox development.
  2. Guarantees confidentiality and tampering rejection (`TamperedCiphertextError`) for sensitive memory fields on disk.
  3. Provides sub-millisecond retrieval (<0.1ms) while decoupling storage from future vector database backends (Qdrant/SQLite-VSS).
- **Consequences**: Key provider interface cleanly abstracts test sandbox keys from future hardware-backed OS Keychain storage.

