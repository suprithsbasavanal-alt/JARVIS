# Jarvis - Autonomous Production-Grade AI Assistant Architecture

**Jarvis** is a modular, scalable, production-ready AI Assistant platform built upon **Clean Architecture** (Hexagonal/Ports & Adapters) and **SOLID Principles**.

---

## 🏛️ System Architecture & Principles

Jarvis separates concerns into distinct layers to maximize testability, maintainability, and independence from external LLM vendors, frameworks, or operating system quirks.

```
                  +-----------------------------------+
                  |         User Interfaces           |
                  |   (Frontend Web / Desktop UI)     |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------+-----------------+
                  |            API Layer              |
                  |  (REST, WebSocket, gRPC, Middleware)|
                  +-----------------+-----------------+
                                    |
                                    v
+-----------------------------------+-----------------------------------+
|                            Core Backend                               |
|                  (Dependency Injection Container)                     |
+-----------------+-----------------+-----------------+-----------------+
                  |                 |                 |
                  v                 v                 v
          +---------------+ +---------------+ +---------------+
          |   AI Engine   | | Memory Module | | Voice Engine  |
          +-------+-------+ +-------+-------+ +-------+-------+
                  |                 |                 |
                  v                 v                 v
          +---------------+ +---------------+ +---------------+
          | Tools Engine  | | Automation    | | OS Integration|
          +-------+-------+ +-------+-------+ +-------+-------+
                  |                 |                 |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------+-----------------+
                  |      Database & Security Layer    |
                  | (Relational, Vector, Guardrails)  |
                  +-----------------------------------+
```

### Clean Architecture Layers
1. **Domain Layer (`contracts/`, `shared/types/`)**: Pure business models, abstract interfaces, and domain exceptions. No external library dependencies.
2. **Use Case Layer (`ai_engine/orchestrator`, `automation/engine`)**: High-level execution flow, reasoning chains, and agent state machines.
3. **Interface Adapters (`api_layer/`, `voice/`, `database/`, `tools/`)**: Translators between external wire protocols (REST/gRPC/WebSocket) and domain contracts.
4. **Infrastructure & Drivers (`os_integration/`, `security/vault`, LLM APIs)**: Hardware hooks, OS processes, secrets storage, and third-party APIs.

---

## 📐 SOLID Principles Applied

- **Single Responsibility Principle (SRP)**: Each folder is a distinct bounded context. For instance, `src/voice/` handles audio processing exclusively, while `src/memory/` manages context retention and retrieval.
- **Open/Closed Principle (OCP)**: Extensible provider interfaces (`BaseLLMProvider`, `BaseMemoryStore`, `BaseTool`, `STTEngine`) allow adding new models, memory storage drivers, or tools without modifying core orchestrator code.
- **Liskov Substitution Principle (LSP)**: Any subclass conforming to interface contracts (e.g. `VectorStore`) can replace another (e.g., Qdrant vs Chroma vs PGVector) with zero side effects.
- **Interface Segregation Principle (ISP)**: Granular, task-focused abstract interfaces prevent clients from depending on methods they do not use.
- **Dependency Inversion Principle (DIP)**: Core services depend strictly on abstract contracts, not concrete classes. Concrete adapters are injected at runtime via dependency injection (`src/backend/container/`).

---

## 📁 Repository Structure Overview

| Directory | Purpose / Module Overview |
| :--- | :--- |
| `config/` | Application settings, environment configuration schema, and structured logging specs. |
| `docs/` | Architecture specs, System Design Documents, ADRs (Architecture Decision Records), and API schemas. |
| `src/ai_engine/` | LLM model abstraction, prompt management, and multi-agent reasoning orchestrators. |
| `src/api_layer/` | REST controllers, WebSocket real-time gateways, gRPC microservice stubs, and API middleware. |
| `src/automation/` | DAG workflow engine, background task schedulers, and event-driven automation triggers. |
| `src/backend/` | Application bootstrap, lifecycle management, and central dependency injection container. |
| `src/dashboard/` | Developer dashboard, live agent inspection UI shell, telemetry, and execution tracing. |
| `src/database/` | Relational ORM models, vector store adapters, migrations (Alembic), and Redis cache wrapper. |
| `src/frontend/` | Web UI & Desktop UI application shells (Stitch MCP design integrated). |
| `src/memory/` | Short-term session buffer, long-term vector semantic storage, working memory scratchpad. |
| `src/os_integration/` | Cross-platform OS hooks, file system watcher, process runner, and native tray notifications. |
| `src/security/` | Auth (JWT/OAuth2), secret vault wrapper, prompt injection guardrails, and PII redactors. |
| `src/shared/` | Base domain types, custom system exceptions, structured logger, and generic helpers. |
| `src/tools/` | Tool registry, isolated execution sandbox, and built-in system/agent tools. |
| `src/voice/` | Speech-to-Text (STT), Text-to-Speech (TTS), audio streaming, and voice activity detection (VAD). |
| `tests/` | Comprehensive test suites: Unit, Integration, End-to-End, Security Guardrails, and Performance. |

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose**
- **Make** (optional)

### Environment Setup
```bash
# 1. Copy environment template
cp config/env.example config/.env

# 2. Spin up infrastructure services (Postgres, Qdrant, Redis)
docker-compose up -d

# 3. Install dependencies in editable mode
pip install -e .
```

---

## 📄 License
MIT License. See `LICENSE` for details.
