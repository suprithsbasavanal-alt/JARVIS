# AI Engine Module (`src/ai_engine`)

## Purpose
The core intelligence engine responsible for model provider abstractions, reasoning orchestrations (ReAct / Chain of Thought), prompt management, and multi-agent coordination.

## Architectural Layer
**Domain Abstraction & Use Case Layer**. Core orchestrators rely exclusively on the `BaseLLMProvider` abstract contract (DIP) to remain agnostic of external LLM vendors (OpenAI, Anthropic, Gemini, local Ollama/vLLM).

## Subdirectories
- `contracts/`: Abstract Base Classes for model providers and agent orchestrators.
- `providers/`: Adapter implementations for model vendors (OpenAI, Anthropic, Gemini, Local).
- `prompts/`: Versioned prompt templates and system instruction managers.
- `orchestrator/`: Reasoning loop, tool call decision parser, and multi-agent dispatcher.
