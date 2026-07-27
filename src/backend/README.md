# Backend Module (`src/backend`)

## Purpose
Serves as the central application composition root, bootstrap entry point, and Dependency Injection Container.

## Architectural Layer
**Composition Root / Application Core (DIP)**. Binds abstract contracts to concrete infrastructure drivers (OpenAI LLM provider, Qdrant Vector store, Redis cache) at runtime initialization.

## Subdirectories
- `container/`: Inversion of Control (IoC) dependency injection container.
- `bootstrap/`: System lifecycle startup, shutdown hooks, and health checks.
