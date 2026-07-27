# Automated Test Suite (`tests/`)

## Purpose
Contains automated test suites covering unit tests, contract compliance tests, integration tests, security guardrail evaluations, and performance benchmarks.

## Subdirectories
- `unit/`: Fast, isolated tests for contracts, entities, and helper functions.
- `integration/`: Multi-module interaction tests with database, vector store, and mock LLMs.
- `e2e/`: Full agent reasoning end-to-end pipeline execution tests.
- `security/`: Prompt injection security scan test vectors.
- `performance/`: Real-time audio latency and throughput benchmarks.
