# Security Module (`src/security`)

## Purpose
Enforces system security boundaries, including authentication (JWT/OAuth2), secret vault encryption, prompt injection protection, PII data redaction, and Role-Based Access Control (RBAC).

## Architectural Layer
**Cross-Cutting Security Guardrail Layer**. Filters incoming inputs and protects sensitive system credentials.

## Subdirectories
- `auth/`: User token verification, permission policies, RBAC.
- `vault/`: Secret management & environment variable encryption wrappers.
- `guardrails/`: Prompt injection scanner, malicious payload redactor, output safety validator.
