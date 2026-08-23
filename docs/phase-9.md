# Phase 9: External Service Integrations & Connector Architecture

## 1. Overview & Architectural Goals

Phase 9 establishes the secure, capability-bounded, and auditable foundation for integrating JARVIS with external third-party services and personal communication channels (Gmail, Google Calendar, Google Drive, Slack, GitHub, Apple Notes, WhatsApp, Telegram).

The external integration layer is designed with strict Defense-in-Depth principles:
1. **Isolated Service Adapters**: Each external service implements a strictly typed `BaseServiceAdapter` contract.
2. **Explicit Capability Manifests**: Services declare granular capabilities (`READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE`, `SEND`, `EXECUTE`). Adapters can never execute undeclared capabilities.
3. **Central Execution Gatekeeper (`ServiceExecutionManager`)**: Every external service request passes through `ServiceExecutionManager`, enforcing connector status, authentication state, emergency stop, capability declarations, PermissionEngine authorization, single-use `ApprovalToken` consumption, and transport safety.
4. **HITL Permission Gating**: High-risk capabilities (`SEND`, `DELETE`, `EXECUTE`, `CREATE`, `UPDATE`) strictly require interactive Human-in-the-Loop (`ApprovalCard`) confirmation and issue single-use cryptographic `ApprovalToken` instances.
5. **Idempotency & Duplicate Protection (`IdempotencyManager`)**: Short-lived SHA-256 mutation fingerprints prevent duplicate external actions and accidental retries of state-modifying requests.
6. **Common Secure HTTP Transport (`SecureHttpTransport`)**: Enforces HTTPS-only, 5 MB request/response payload limits, concurrency limits (10 concurrent requests), exponential backoff with jitter on idempotent methods, HTTP 429 `Retry-After` ceiling handling, and automatic header sanitization (`Authorization`, `X-API-Key`, `Cookie`).
7. **Platform-Isolated Credential Boundary**: Credential providers (`SecureCredentialManager`, `BaseSecureStorage`) isolate OAuth2 tokens, API keys, and Bot tokens in memory or OS Keychain. Plaintext credentials are never exposed via status endpoints, metadata dictionaries, string representations, or audit logs.
8. **Non-Repudiable Chained Audit Trail**: Every service operation, registration, enablement, disablement, and revocation writes to the SHA-256 chained audit logger with automated sensitive parameter scrubbing (`[REDACTED]`).
9. **Network Safety by Default**: Real external network access is disabled by default (`SystemConfig.enable_external_services = False`).

---

## 2. Service Integration Layer Architecture

```
AgentLoop
   │
   ▼
ToolRegistry
   │
   ▼
ServiceRegistry
   │
   ▼
ServicePermissionBridge ──► PermissionEngine (HITL ApprovalCard)
   │
   ▼
ApprovalToken Validation & Single-Use Consumption
   │
   ▼
ServiceExecutionManager (Emergency Stop & Revocation Checks)
   │
   ├──► IdempotencyManager (Duplicate Mutation Guard)
   │
   ├──► SecureCredentialManager (Token Retrieval & Isolation)
   │
   └──► SecureHttpTransport / MockHttpTransport (HTTPS, Payload Limits, Concurrency)
           │
           ▼
    External Service API (Gmail, Calendar, Drive, Slack, GitHub)
```

---

## 3. Capability Model (`services/models.py`)

| Capability | Permission Level | Description | Example Operations |
| :--- | :--- | :--- | :--- |
| `READ` | `NORMAL` | Non-destructive data retrieval | `read_inbox`, `list_events`, `list_files`, `read_channel_history`, `list_issues` |
| `SEARCH` | `NORMAL` | Read-only index queries and contact filtering | `search_emails`, `search_events`, `search_files`, `search_messages`, `search_issues` |
| `CREATE` | `SENSITIVE` | Resource generation (Requires HITL) | `create_draft`, `create_event`, `upload_file`, `create_issue` |
| `UPDATE` | `SENSITIVE` | Resource modification (Requires HITL) | `update_event`, `update_file`, `update_issue` |
| `DELETE` | `SENSITIVE` | Resource removal / Trashing (Requires HITL) | `delete_email`, `delete_event`, `delete_file`, `delete_message`, `close_issue` |
| `SEND` | `SENSITIVE` | Outbound external transmission (Requires HITL) | `send_email`, `post_message` |
| `EXECUTE` | `SENSITIVE` | Service-side automation execution (Requires HITL) | `trigger_webhook`, `run_sync` |

---

## 4. Specific Connectors & Adapters (`services/connectors/`)

### 4.1 Connector Matrix

| Connector | Service ID | Auth Classification | Declared Capabilities | Operations Supported |
| :--- | :--- | :--- | :--- | :--- |
| **Gmail** | `gmail` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `SEND`, `DELETE` | `read_inbox`, `get_email`, `search_emails`, `create_draft`, `send_email`, `delete_email` |
| **Google Calendar** | `google_calendar` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_events`, `get_event`, `search_events`, `create_event`, `update_event`, `delete_event` |
| **Google Drive** | `google_drive` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_files`, `read_file`, `search_files`, `upload_file`, `update_file`, `delete_file` |
| **Slack** | `slack` | `BOT_TOKEN` | `READ`, `SEARCH`, `SEND`, `DELETE` | `read_channel_history`, `get_message`, `search_messages`, `post_message`, `delete_message` |
| **GitHub** | `github` | `PERSONAL_ACCESS_TOKEN` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_issues`, `get_issue`, `search_issues`, `create_issue`, `update_issue`, `close_issue` |

---

## 5. Common Transport & Execution Gate (`services/transport/`, `services/execution/`)

### 5.1 Transport Security Guarantees (`SecureHttpTransport`)
- **Scheme Verification**: Rejects any non-HTTPS URL with `InsecureTransportError`.
- **Payload Bounds**: Enforces hard maximums on request body (5 MB) and response body (5 MB) to prevent denial of service.
- **Concurrency Bounds**: Bounded by `asyncio.Semaphore(10)`.
- **Idempotent Retries**: Automatically retries idempotent methods (`GET`, `HEAD`, `OPTIONS`, `PUT`, `DELETE`) up to 3 times with exponential backoff and jitter. Non-idempotent `POST` requests are never retried unless an `idempotency_key` is supplied.
- **Throttling & Backoff**: Respects HTTP 429 `Retry-After` headers up to a 30s ceiling.
- **Header Scrubbing**: Automatically scrubs `Authorization`, `X-API-Key`, and `Cookie` headers in representations and error traces.

### 5.2 Idempotency & Duplicate Guard (`IdempotencyManager`)
- Computes deterministic SHA-256 fingerprint from `service_id`, `operation`, and parameters.
- Maintains in-memory LRU cache of 1000 items with a 15-minute TTL.
- Detects concurrent in-flight duplicates and raises `DuplicateExecutionError`.
- Returns cached responses for completed mutations, eliminating duplicate outbound emails, messages, or issues.

---

## 6. Security & Invariant Verification Matrix

| Subsystem / Invariant | Enforcement Mechanism | Verification Test |
| :--- | :--- | :--- |
| **Capability Boundaries** | Explicit `validate_capability` checks against declared set | `test_undeclared_capability_rejected_by_execution_manager` |
| **HITL Authorization Gate** | `HumanConfirmationRequiredError` on SENSITIVE capabilities without token | `test_execution_manager_mutation_hitl_and_token_consumption` |
| **Single-Use Approval Tokens** | Token replay rejection via `ApprovalToken.is_consumed` | `test_execution_manager_mutation_hitl_and_token_consumption` |
| **Emergency Stop** | Immediate fail-closed halt of external execution | `test_execution_manager_emergency_stop_halts_execution` |
| **Connector Revocation** | Revoking connector blocks subsequent calls | `test_execution_manager_revocation_blocks_execution` |
| **Idempotency Protection** | Fingerprint caching prevents duplicate mutation | `test_idempotency_prevents_duplicate_mutation` |
| **Insecure URL Rejection** | Rejects `http://` schemes | `test_insecure_http_url_rejection` |
| **Payload Size Bounds** | Maximum 5 MB request/response limit | `test_transport_payload_size_limits` |
| **Secret Scrubbing** | Automatic parameter and header redaction | `test_transport_sensitive_header_redaction`, `test_audit_log_chained_integrity_and_secret_redaction` |
| **Network Safety** | `SystemConfig.enable_external_services = False` by default | `test_transport_external_services_disabled_check` |

---

## 7. Automated Test Suites

- `tests/test_phase9_1_services.py` (19 automated tests).
- `tests/test_phase9_2_connectors.py` (15 automated tests).
- `tests/test_phase9_3_auth.py` (11 automated tests).
- `tests/test_phase9_4_external_execution.py` (15 automated tests).
- Total repository tests: **337/337 passing 100% (in 1.418s)**.
