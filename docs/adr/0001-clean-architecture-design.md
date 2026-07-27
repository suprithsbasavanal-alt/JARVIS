# ADR 0001: Clean Architecture Foundation for Jarvis

* **Status**: Accepted
* **Date**: 2026-07-27
* **Context**: Building an enterprise-ready AI assistant requires high modularity, testability, and resilience against vendor lock-in (e.g., changes in LLM providers, database backends, or UI frameworks).

## Decision
We adopt **Clean Architecture (Hexagonal Architecture / Ports & Adapters)** combined with **SOLID principles**.

1. **Domain Abstraction**: Core business contracts (`src/ai_engine/contracts`, `src/memory/contracts`, `src/tools/contracts`, etc.) will have zero external framework or vendor dependencies.
2. **Dependency Injection**: Concrete infrastructure implementations will be registered in `src/backend/container/` and injected dynamically into use case services.
3. **Pluggable Architecture**: LLM providers, voice models, vector stores, and tools will expose abstract interfaces conforming to Open/Closed and Liskov Substitution principles.

## Consequences
- **Positive**:
  - Independent of LLM vendors (switch between OpenAI, Anthropic, Gemini, or local models without modifying business logic).
  - High testability (unit tests mock contracts without needing real API keys or DB instances).
  - Clean separation of UI, API, Voice, Automation, and Security modules.
- **Negative**:
  - Requires maintaining explicit abstract base class (`abc.ABC`) interface definitions.
