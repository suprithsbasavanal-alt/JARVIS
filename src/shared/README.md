# Shared Utilities Module (`src/shared`)

## Purpose
Provides core domain primitives, generic types, standardized exception hierarchies, and structured logging capabilities used across all other Jarvis modules.

## Architectural Layer
**Domain Layer / Core Foundation**. It has zero external dependencies on third-party frameworks or databases.

## Module Components
- `types/`: Domain entity base classes, value objects, and execution status enums.
- `exceptions/`: Domain exception taxonomy for granular error catching and HTTP mapping.
- `logger/`: Centralized structured logger wrapper.
