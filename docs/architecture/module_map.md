# Jarvis Module Responsibility Matrix

| Module Directory | Primary Responsibility | Key Interfaces / Base Classes | SOLID Principles Highlight |
| :--- | :--- | :--- | :--- |
| `src/ai_engine` | Model orchestration, prompt versioning, agent loop | `BaseLLMProvider`, `AgentOrchestrator`, `PromptTemplate` | **OCP**: Add new LLM vendors without modifying orchestrator logic. |
| `src/api_layer` | HTTP, WebSocket streaming, gRPC stubs, rate limits | `BaseController`, `APIResponse`, `MiddlewareContract` | **SRP**: Deals strictly with serialization & wire protocols. |
| `src/automation` | Workflow DAG execution, cron scheduling, event triggers | `WorkflowEngine`, `BaseTrigger`, `SchedulerService` | **DIP**: Depends on abstract triggers and action contracts. |
| `src/backend` | App lifecycle, dependency injection container, bootstrap | `Container`, `ApplicationBootstrap` | **DIP**: Injects concrete singletons at runtime. |
| `src/dashboard` | Telemetry collection, live agent state inspector UI | `TraceCollector`, `DashboardInspector` | **ISP**: Segregated telemetry interface for non-blocking inspection. |
| `src/database` | ORM entities, vector storage, Redis caching, migrations | `RepositoryPattern`, `VectorStore`, `CacheClient` | **LSP**: Vector stores (Qdrant/PGVector) can be swapped seamlessly. |
| `src/frontend` | Web & Desktop user interface application shells | `UIController`, `StateStore`, `ComponentRegistry` | **SRP**: UI rendering decoupled from backend execution. |
| `src/memory` | Short-term buffer, RAG long-term vector, working scratchpad | `BaseMemoryStore`, `VectorMemory`, `WorkingMemory` | **ISP**: Fine-grained interfaces for reading vs writing memory. |
| `src/os_integration` | Local file watching, process running, native tray hooks | `FSWatcher`, `ProcessRunner`, `NativeTray` | **SRP**: OS specific logic encapsulated isolated from business domain. |
| `src/security` | Auth (JWT/OAuth), secret vault, prompt sanitization | `AuthService`, `SecretVault`, `GuardrailScanner` | **SRP & LSP**: Modular security validators filter malicious inputs. |
| `src/shared` | Core types, system exceptions, structured logger | `BaseDomainEntity`, `JarvisException`, `LoggerContract` | **SRP**: Zero external dependencies domain primitives. |
| `src/tools` | Tool registry, isolated sandbox environment, builtins | `BaseTool`, `ToolSandbox`, `ToolRegistry` | **OCP & LSP**: Plugins added safely to registry. |
| `src/voice` | Speech-to-text, text-to-speech, audio VAD buffer | `STTEngine`, `TTSEngine`, `AudioStreamBuffer` | **OCP**: Hot-swap voice providers based on audio quality/speed. |
