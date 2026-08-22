# JARVIS — Personal AI Assistant

> **PHASE 1 — SAFE SANDBOX CORE ONLY**

JARVIS is a private, security-first personal AI assistant built for **macOS** and **Android**.

---

## ⚠️ Phase 0 Notice & Safety Guardrails

**This repository is strictly in Phase 0 (Architecture & Security Design).**

In compliance with safety principles:
- ❌ **No system capabilities or daemons are installed on the host.**
- ❌ **No personal files, credentials, or private databases are accessed.**
- ❌ **Microphone, camera, and screen recording are disabled/unimplemented.**
- ❌ **No external accounts (Google, Apple, WhatsApp, Telegram, etc.) are connected.**
- ❌ **No arbitrary commands, email sending, message dispatching, or transactions can execute.**
- ✅ **All tools and workflows operate exclusively against an isolated, mock development sandbox (`sandbox/`).**

---

## Architectural Principles

1. **Least Privilege & Default Deny**: Every tool, action, and API requires explicit capability permissions. Unregistered actions fail closed.
2. **Deterministic Human Confirmation**: Sensitive and destructive actions (e.g., communication, file modification, purchasing) require an interactive cryptographic approval token.
3. **Data Minimization & Zero-Trust Privacy**: Personal data and secrets are never passed to external LLM providers unredacted.
4. **Provider-Agnostic Model Routing**: Abstract routing separates reasoning, fast responses, and confidential local processing (Ollama/Llama.cpp).
5. **Epistemic Honesty & Independence**: JARVIS addresses the user as "Suprith" in private contexts and "Sir" in formal/public contexts, can respectfully disagree with technical or logical errors, and never assumes physical presence without explicit context.

---

## Project Structure

```
JARVIS-gpt/
├── README.md              # Project mission & safety declarations
├── PHASES.md              # 14-Phase development roadmap & gatekeepers
├── pyproject.toml         # Python 3.12+ project & strict typing specs
├── config/                # Validated configuration schemas
├── core/                  # Event bus, context manager, base types
├── security/              # Auth, permissions, prompt guard, vault, audit
├── model_routing/         # Multi-provider model router & prompt sanitizer
├── memory/                # Ephemeral, encrypted episodic, and vault memory
├── conversation/          # Session manager, dialogue state, persona engine
├── agents/                # Core agent execution loop & planning pipeline
├── tools/                 # Tool contracts, parameter schemas, safety tiers
├── integrations/          # Abstract contracts for future service integrations
├── voice/                 # Speech pipeline contracts (Wake, STT, TTS)
├── intelligence/          # Proactive suggestion & reasoning engines
├── sandbox/               # Isolated mock filesystem & synthetic services
├── desktop/               # macOS Desktop client architecture specs
├── android/               # Android client architecture specs
├── docs/                  # In-depth architectural & security specifications
└── tests/                 # Unit, security, and sandbox isolation test suites
```

---

## Documentation Index

- [Architecture Overview](docs/architecture.md)
- [Security Architecture](docs/security.md)
- [Threat Model & Risk Matrix](docs/threat-model.md)
- [Permission Model & Action Policies](docs/permissions.md)
- [Memory Architecture & Privacy](docs/memory.md)
- [Agent Execution Loop](docs/agent-loop.md)
- [Integration Contracts](docs/integrations.md)
- [Voice Processing Architecture](docs/voice.md)
- [Testing Strategy](docs/testing.md)
- [Deployment & Emergency Protocols](docs/deployment.md)
- [Architecture Decision Records (ADRs)](docs/decisions.md)

---

## Verification & Safe Development

Run the safe Phase 0 test suite and type check:

```bash
# Run isolated unit, security, and sandbox tests
pytest -v

# Run strict type checking
mypy core security model_routing memory conversation agents tools integrations voice intelligence sandbox tests
```

---

## Roadmap

See [PHASES.md](PHASES.md) for the phased progression from Phase 0 to Phase 13.
No progression to Phase 1 occurs without explicit human approval.
