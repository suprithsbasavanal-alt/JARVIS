# Phase 7 — macOS Desktop Agent & Secure IPC

> **Phase 7 Architectural Specification & Verification Report**

---

## 1. Overview & Objectives

JARVIS Phase 7 establishes the **macOS Desktop Agent**, providing a native, high-performance interface with Advanced Glassmorphism visual design, background daemon execution, and a secure local Unix Domain Socket / JSON-RPC 2.0 Inter-Process Communication (IPC) bridge.

### Core Deliverables
1. **Tauri v2 Desktop Shell (`desktop/src-tauri/`)**:
   - Native macOS AppKit vibrancy (`NSVisualEffectView`), window lifecycle management, system tray status menu, and global shortcuts (`Cmd+Space` HUD, `Cmd+Shift+Esc` Emergency Stop).
   - Granular least-privilege ACL capabilities (`desktop/src-tauri/capabilities/default.json`).
2. **Stitch-Designed Aether HUD Frontend (`desktop/ui/`)**:
   - Advanced Glassmorphism dark mode with `backdrop-filter: blur(24px) saturate(190%)`, Electric Cyan (`#00f2ff`) / Auric Gold accents, and Geist/Inter typography.
   - Spotlight-style search/command bar (`HudModal.ts`), live streaming conversation view (`ConversationView.ts`), proactive advisory drawer (`ProactiveAdvisoryWidget.ts`), interactive HITL confirmation modal (`ApprovalModal.ts`), and persistent plan checklist (`PlanChecklistView.ts`).
3. **Secure Python IPC Server & Daemon (`core/ipc_server.py`, `desktop/daemon.py`)**:
   - Unix Domain Socket (`/tmp/jarvis_daemon.sock`) enforcing POSIX `0700` user permissions.
   - Typed JSON-RPC 2.0 protocol with cryptographic auth token handshake.
   - Full integration with `AgentLoop`, `EventBus`, `ProactiveRuntimeBridge`, `MemoryManager`, and `AuditLogger`.

---

## 2. IPC Protocol Specification (JSON-RPC 2.0)

All communication between the Tauri frontend / native client and the Python core daemon occurs over a local Unix Domain Socket with JSON-RPC 2.0 framing (newline-delimited JSON).

```
┌─────────────────────────┐                            ┌────────────────────────┐
│  Tauri v2 (Aether HUD)  │                            │  JARVIS Python Daemon  │
│      Renderer / Rust    │                            │     (IPCServer)        │
└────────────┬────────────┘                            └───────────┬────────────┘
             │                                                     │
             │ 1. Handshake (auth_token)                           │
             ├────────────────────────────────────────────────────>│
             │<────────────────────────────────────────────────────┤
             │    { "authenticated": true, "version": "0.7.0" }    │
             │                                                     │
             │ 2. Turn Request (query, proactive_advisory)         │
             ├────────────────────────────────────────────────────>│
             │                                                     │
             │ 3. Human Confirmation Card (Sensitive Tool)         │
             │<────────────────────────────────────────────────────┤
             │    { "status": "AWAITING_CONFIRMATION", ... }       │
             │                                                     │
             │ 4. User Approval / Decision (APPROVE + Token)       │
             ├────────────────────────────────────────────────────>│
             │<────────────────────────────────────────────────────┤
             │    { "status": "COMPLETED", "reply": "..." }        │
             │                                                     │
             │ 5. Emergency Stop (`Cmd+Shift+Esc`)                 │
             ├────────────────────────────────────────────────────>│
             │    Revoke tokens, cancel execution                  │
             │<────────────────────────────────────────────────────┤
             │    { "status": "STOPPED" }                          │
```

### JSON-RPC Registered Methods

| Method | Parameters | Description | Security Controls |
| :--- | :--- | :--- | :--- |
| `jarvis.handshake` | `{"auth_token": "..."}` | Authenticates desktop client connection | Rejects invalid tokens with code `-32001` |
| `jarvis.status` | `{}` | Returns system health, agent state, tool counts | Requires authentication |
| `jarvis.session.create` | `{"user_name": "...", "permission_level": "..."}` | Initializes a new conversational session | Publishes `SESSION_STARTED` event |
| `jarvis.session.get` | `{"session_id": "..."}` | Retrieves active session state | Validates session existence |
| `jarvis.turn.process` | `{"session_id": "...", "query": "..."}` | Executes 11-step turn via `AgentLoop` | Returns approval card for sensitive actions |
| `jarvis.approval.respond` | `{"card_id": "...", "decision": "APPROVE"\|"DENY"}` | Submits human authorization decision | Issues single-use `ApprovalToken` |
| `jarvis.proactive.get_latest` | `{"session_id": "..."}` | Fetches latest proactive advisory | Enforces `is_informational_only = True` |
| `jarvis.plan.get_active` | `{"plan_id": "..."}` | Fetches active study/task plan with step states | Read-only representation |
| `jarvis.plan.update_step` | `{"plan_id": "...", "step_number": 1, "completed": true}` | Updates plan checklist checkbox | Isolated in-memory/store state |
| `jarvis.system.emergency_stop` | `{}` | Revokes all active tokens, halts actions | Non-repudiable audit logging |

---

## 3. Security Invariants & Hardening

1. **POSIX File Permissions (`0700`)**: Unix Domain Socket file is created with `0o700` mode, preventing access by any other OS user on the local system.
2. **Ephemeral Auth Token Handshake**: Unauthenticated calls receive `-32000 Authentication required`.
3. **Zero Autonomous Tool Execution**: Proactive advisories displayed in the UI remain purely informational and cannot trigger tool calls without explicit human turn submission.
4. **Interactive HITL Confirmation**: Sensitive and destructive tools require user authorization through the `ApprovalModal`, which generates single-use cryptographic `ApprovalToken`s.
5. **Secret Scrubbing**: Subprocess environment and JSON-RPC status responses are scrubbed of all host API keys and tokens.
6. **Emergency Stop**: Instant token revocation and execution cancellation via global hotkey (`Cmd+Shift+Esc`) or UI button.

---

## 4. Verification & Testing

The Phase 7 implementation was validated with **16 dedicated automated tests** in `tests/test_phase7_desktop.py`, bringing the total repository test suite to **227 passing tests (100% pass rate in 1.28s)**:

- `test_ipc_socket_creation_and_permissions`: Validates socket creation and `0700` permissions.
- `test_unauthenticated_request_rejected`: Validates rejection of unauthenticated commands (`-32000`).
- `test_invalid_auth_token_rejected`: Validates invalid token rejection (`-32001`).
- `test_invalid_method_rejected`: Validates unknown method handling (`-32601`).
- `test_status_command`: Validates status reporting over IPC.
- `test_session_create_and_get`: Validates session creation and retrieval.
- `test_turn_process_normal_flow`: Validates end-to-end turn processing over IPC.
- `test_hitl_approval_deny_flow`: Validates HITL approval card delivery and user denial.
- `test_hitl_approval_approve_flow`: Validates single-use token issuance and tool execution upon user approval.
- `test_proactive_advisory_retrieval`: Validates formatted XML and Markdown advisory retrieval.
- `test_plan_management_and_step_persistence`: Validates study/task plan step checkbox updates.
- `test_emergency_stop_command`: Validates emergency token revocation.
- `test_proactive_advisory_cannot_trigger_unsolicited_tools_over_ipc`: Validates informational-only boundary.
- `test_secret_isolation_over_ipc`: Validates that secret keys are never exposed over IPC.
- `test_malformed_json_payload_rejection`: Validates `-32700 Parse error` on invalid JSON.
- `test_backend_unavailable_error_handling`: Validates client connection error handling when daemon is offline.
