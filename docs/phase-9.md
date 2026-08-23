# Phase 9: External Service Integrations & Connector Architecture

## 1. Overview & Architectural Goals

Phase 9 establishes the secure, capability-bounded, and auditable foundation for integrating JARVIS with external third-party services and personal communication channels (Gmail, Google Calendar, Google Drive, Slack, GitHub, Apple Notes, WhatsApp, Telegram).

The external integration layer is designed with strict Defense-in-Depth principles:
1. **Isolated Service Adapters**: Each external service implements a strictly typed `BaseServiceAdapter` contract.
2. **Explicit Capability Manifests**: Services declare granular capabilities (`READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE`, `SEND`, `EXECUTE`). Adapters can never execute undeclared capabilities.
3. **HITL Permission Gating**: High-risk capabilities (`SEND`, `DELETE`, `EXECUTE`, `CREATE`, `UPDATE`) strictly require interactive Human-in-the-Loop (`ApprovalCard`) confirmation and issue single-use cryptographic `ApprovalToken` instances.
4. **Platform-Isolated Credential Boundary**: Credential providers (`SecureCredentialManager`, `BaseSecureStorage`) isolate OAuth2 tokens, API keys, and Bot tokens in memory or OS Keychain. Plaintext credentials are never exposed via status endpoints, metadata dictionaries, string representations, or audit logs.
5. **Non-Repudiable Chained Audit Trail**: Every service operation, registration, enablement, disablement, and revocation writes to the SHA-256 chained audit logger with automated sensitive parameter scrubbing (`[REDACTED]`).
6. **Bounded Health Monitoring & Fault Isolation**: Asynchronous health checks, execution timeouts (15s), and deterministic simulation hooks prevent external API latency from hanging the central `AgentLoop`.
7. **Network Safety by Default**: Real external network access is disabled by default (`SystemConfig.enable_external_services = False`).

---

## 2. Service Integration Layer (`services/`)

### 2.1 Capability Model (`services/models.py`)

| Capability | Permission Level | Description | Example Operations |
| :--- | :--- | :--- | :--- |
| `READ` | `NORMAL` | Non-destructive data retrieval | `read_inbox`, `list_events`, `list_files`, `read_channel_history`, `list_issues` |
| `SEARCH` | `NORMAL` | Read-only index queries and contact filtering | `search_emails`, `search_events`, `search_files`, `search_messages`, `search_issues` |
| `CREATE` | `SENSITIVE` | Resource generation (Requires HITL) | `create_draft`, `create_event`, `upload_file`, `create_issue` |
| `UPDATE` | `SENSITIVE` | Resource modification (Requires HITL) | `update_event`, `update_file`, `update_issue` |
| `DELETE` | `SENSITIVE` | Resource removal / Trashing (Requires HITL) | `delete_email`, `delete_event`, `delete_file`, `delete_message`, `close_issue` |
| `SEND` | `SENSITIVE` | Outbound external transmission (Requires HITL) | `send_email`, `post_message` |
| `EXECUTE` | `SENSITIVE` | Service-side automation execution (Requires HITL) | `trigger_webhook`, `run_sync` |

### 2.2 Lifecycle & Status Model (`ServiceStatus`)

- `CONNECTED`: Active, healthy, credentials valid.
- `DISCONNECTED`: Configured but currently offline.
- `AUTH_REQUIRED`: Credentials missing, expired, or require re-auth.
- `AUTHENTICATING`: In the process of OAuth flow or key verification.
- `DEGRADED`: Experiencing elevated latency or transient rate-limits (HTTP 429).
- `REVOKED`: Explicitly revoked/disabled by user; credentials zeroized.
- `ERROR`: Unrecoverable error state or upstream outage (HTTP 503).

---

## 3. Specific Connectors & Adapters (`services/connectors/`)

### 3.1 Connector Matrix

| Connector | Service ID | Auth Classification | Declared Capabilities | Operations Supported |
| :--- | :--- | :--- | :--- | :--- |
| **Gmail** | `gmail` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `SEND`, `DELETE` | `read_inbox`, `get_email`, `search_emails`, `create_draft`, `send_email`, `delete_email` |
| **Google Calendar** | `google_calendar` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_events`, `get_event`, `search_events`, `create_event`, `update_event`, `delete_event` |
| **Google Drive** | `google_drive` | `OAUTH2` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_files`, `read_file`, `search_files`, `upload_file`, `update_file`, `delete_file` |
| **Slack** | `slack` | `BOT_TOKEN` | `READ`, `SEARCH`, `SEND`, `DELETE` | `read_channel_history`, `get_message`, `search_messages`, `post_message`, `delete_message` |
| **GitHub** | `github` | `PERSONAL_ACCESS_TOKEN` | `READ`, `SEARCH`, `CREATE`, `UPDATE`, `DELETE` | `list_issues`, `get_issue`, `search_issues`, `create_issue`, `update_issue`, `close_issue` |

---

## 4. Secure Authentication & Credential Lifecycle (`services/credentials/`)

Phase 9.3 implements the platform-secure authentication architecture:

```
                  ┌─────────────────────────────────────────────────┐
                  │           SecureCredentialManager               │
                  │   (implements BaseCredentialProvider)           │
                  └────────┬──────────────────────────────┬─────────┘
                           │                              │
             ┌─────────────▼────────────┐   ┌─────────────▼────────────┐
             │   InMemorySecureStorage  │   │   KeychainSecureStorage  │
             │   (Deterministic Tests)  │   │   (macOS Hardware Store) │
             └──────────────────────────┘   └──────────────────────────┘
```

### 4.1 OAuth 2.0 Security Architecture (`OAuth2LifecycleManager`)
1. **CSRF State Generation**: Generates 256-bit cryptographically random tokens (`secrets.token_urlsafe(32)`) with a 10-minute TTL.
2. **Single-Use State Enforcement**: Consumes state token upon first verification, preventing replay attacks.
3. **Cross-Service Isolation**: State checks verify both token and `service_id`.
4. **Token Refresh Lifecycle**: Automatic calculation of `expires_at` with a 60-second safety buffer; seamless refresh without exposing secrets.
5. **Revocation & Purge**: Revoking an adapter removes credentials from storage and invalidates active session tokens.

### 4.2 Service Authentication Matrix

| Service | Protocol | Scopes / Identifier | Storage Format |
| :--- | :--- | :--- | :--- |
| **Gmail** | OAuth 2.0 PKCE | `gmail.readonly`, `gmail.send`, `gmail.modify` | `OAuth2Credentials` |
| **Google Calendar** | OAuth 2.0 PKCE | `calendar.readonly`, `calendar.events` | `OAuth2Credentials` |
| **Google Drive** | OAuth 2.0 PKCE | `drive.readonly`, `drive.file` | `OAuth2Credentials` |
| **Slack** | Bot Token | `channels:history`, `chat:write`, `search:read` | `BotTokenCredentials` |
| **GitHub** | Personal Access Token | `repo`, `read:org`, `issues` | `ApiTokenCredentials` |

---

## 5. Security & Invariant Verification Matrix

| Subsystem / Invariant | Enforcement Mechanism | Phase 9 Verification |
| :--- | :--- | :--- |
| **Capability Boundaries** | Explicit `validate_capability` checks against declared set | `test_undeclared_capability_rejection_across_connectors` |
| **HITL Authorization Gate** | `HumanConfirmationRequiredError` on SENSITIVE capabilities without token | `test_gmail_send_and_delete_hitl_enforcement`, `test_calendar_create_update_delete_hitl`, `test_drive_read_and_upload_hitl`, `test_slack_read_and_post_message_hitl`, `test_github_read_and_create_issue_hitl` |
| **Single-Use Approval Tokens** | Token replay rejection via `ApprovalToken.is_consumed` | `test_token_replay_rejected_across_connectors` |
| **Credential Isolation** | `SecureCredentialManager` zeroization and non-disclosure | `test_credential_models_redaction_and_expiry`, `test_credential_manager_rotation_and_revocation` |
| **OAuth2 CSRF Protection** | Single-use 256-bit state tokens with TTL | `test_oauth_authorization_url_and_csrf_state`, `test_oauth_state_expiration_and_mismatch` |
| **OAuth2 Token Refresh** | Bounded expiration calculation and error isolation | `test_oauth_code_exchange_and_token_refresh`, `test_oauth_refresh_failure_isolation` |
| **Secret Scrubbing** | Automatic parameter redaction in `AuditLogger` and exceptions | `test_audit_trail_and_ipc_secrecy` |
| **Network Safety** | `SystemConfig.enable_external_services = False` by default | `test_external_services_disabled_by_default` |

---

## 6. Automated Test Suites

- `tests/test_phase9_1_services.py` (19 automated tests).
- `tests/test_phase9_2_connectors.py` (15 automated tests).
- `tests/test_phase9_3_auth.py` (11 automated tests).
- Total repository tests: **322/322 passing 100% (in 1.409s)**.
