# Tools Module (`src/tools`)

## Purpose
Manages tool definitions, tool registries, execution security verification, and isolated execution sandboxes for Jarvis capabilities (web search, calculator, file I/O, terminal commands).

## Architectural Layer
**Domain Abstraction & Interface Adapter Layer**. Every tool must implement `BaseTool`, allowing dynamic discovery and safe plugin additions without core code modification (OCP).

## Subdirectories
- `contracts/`: Abstract Base Classes (`BaseTool`, `ToolSandboxContract`, `ToolResult`).
- `registry/`: Dynamic tool registry, permission manager, and metadata index.
- `sandbox/`: Security boundary for executing Python code or subprocesses safely.
- `builtins/`: Core standard tools provided out of the box.
