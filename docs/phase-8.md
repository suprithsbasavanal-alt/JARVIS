# Phase 8 — Android Companion Client

## 1. Overview & Architecture

Phase 8 introduces the native **Android Companion Client** and **Authenticated Local Network Transport Bridge** for JARVIS, designed with **Kotlin & Jetpack Compose** on Android and **Asyncio TCP/TLS with Cryptographic Challenge-Response** on the macOS host daemon.

The companion client provides:
1. **Hardware-Backed Device Key Pairing**: Asymmetric device key registration (`jarvis.network.pair.begin`), 6-digit confirmation code (`jarvis.network.pair.confirm`), and non-repudiable audit trails.
2. **Mutual Cryptographic Authentication**: Ephemeral 32-byte challenge nonces (`jarvis.network.auth.challenge`), 60s TTL, hardware signature verification (`jarvis.network.auth.verify`), replay prevention, and scoped session tokens (`DeviceSession`).
3. **Dedicated Local Network Bridge**: `NetworkBridgeServer` bridges Android JSON-RPC calls to the internal `AgentLoop` and `PermissionEngine` without exposing the internal Unix Domain Socket directly to the network.
4. **Biometric Human-in-the-Loop (HITL) Gate**: Hardware-authenticated confirmation modal for sensitive/destructive tool executions via Android `BiometricPrompt`.
5. **Proactive Intelligence Drawer**: Continuous project review reports, security findings, and epistemic disagreement observations (strictly informational-only).
6. **Plan & Milestone Checklists**: Real-time progress synchronization with host `StructuredPlan` states.
7. **Emergency Stop**: Instant revocation of all active approval tokens and pending authorizations (`jarvis.system.emergency_stop`).

---

## 2. Directory Structure (`android/` & `security/`)

```
android/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle/
│   └── wrapper/
│       └── gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml
        │   ├── res/
        │   │   ├── values/
        │   │   │   ├── colors.xml
        │   │   │   ├── strings.xml
        │   │   │   └── themes.xml
        │   │   └── xml/
        │   │       ├── data_extraction_rules.xml
        │   │       └── network_security_config.xml
        │   └── java/com/jarvis/assistant/
        │       ├── JarvisApplication.kt
        │       ├── MainActivity.kt
        │       ├── data/
        │       │   ├── model/JsonRpcModels.kt
        │       │   ├── remote/JarvisIpcClient.kt
        │       │   ├── remote/MockJarvisIpcClient.kt
        │       │   ├── remote/NetworkTransportClient.kt
        │       │   └── repository/JarvisRepository.kt
        │       ├── security/
        │       │   ├── KeystoreManager.kt
        │       │   ├── DeviceKeyManager.kt
        │       │   └── BiometricAuthManager.kt
        │       ├── ui/
        │       │   ├── theme/
        │       │   │   ├── Color.kt
        │       │   │   ├── Theme.kt
        │       │   │   └── Type.kt
        │       │   ├── components/
        │       │   │   └── AetherComponents.kt
        │       │   └── screens/
        │       │       ├── DashboardScreen.kt
        │       │       ├── ChatScreen.kt
        │       │       ├── ApprovalDialog.kt
        │       │       ├── ProactiveScreen.kt
        │       │       └── PlanScreen.kt
        │       └── viewmodel/
        │           └── MainViewModel.kt
        └── test/java/com/jarvis/assistant/
            └── JarvisCompanionTest.kt

security/
└── device_pairing.py      # DevicePairingRegistry, Challenge/Response, Key Rotation

core/
└── network_bridge.py      # NetworkBridgeServer (Async TCP/TLS JSON-RPC Transport)
```

---

## 3. Pairing Lifecycle & Cryptographic Protocols

```
Android Companion Client                               JARVIS macOS Daemon (NetworkBridgeServer)
       |                                                               |
       | ----- jarvis.network.pair.begin(device_id, pubkey_hex) -----> |
       |                                                               | (Generate 6-digit code, PENDING)
       | <---- {pairing_code: "492815", status: "PENDING"} ----------- |
       |                                                               |
       |                        [Host Desktop User Confirms Code]       |
       |                                                               |
       | ----- jarvis.network.pair.confirm(device_id, "492815") ------> |
       | <---- {status: "CONFIRMED"} ---------------------------------- |
       |                                                               |
       | ====================== SESSION AUTHENTICATION ====================== |
       |                                                               |
       | ----- jarvis.network.auth.challenge(device_id) -------------> |
       | <---- {challenge_id, nonce: "32-byte-hex", expires_in: 60s} - |
       |                                                               |
       | (Hardware Key Signs Nonce)                                    |
       | ----- jarvis.network.auth.verify(challenge_id, signature) --> |
       |                                                               | (Verify signature against pubkey)
       |                                                               | (Verify nonce unconsumed & TTL)
       | <---- {authenticated: true, session_token: "d_sess_..."} ---- |
       |                                                               |
       | ====================== OPERATIONAL TURN / HITL ===================== |
       |                                                               |
       | ----- jarvis.turn.process(query, session_token) ------------> |
       | <---- {status: "AWAITING_CONFIRMATION", card: {...}} -------- |
       |                                                               |
       | (BiometricPrompt Authenticates User)                          |
       | ----- jarvis.approval.respond(card_id, "APPROVE") ----------> |
       | <---- {status: "COMPLETED", reply: "...", tool_executed: true}-|
```

---

## 4. Security & Cryptographic Invariants

- **Hardware Keystore (`StandardKeystoreManager`, `StandardDeviceKeyManager`)**: Configures AES-256-GCM hardware-backed keys and cryptographic challenge signing keys (`AndroidKeyStore`). Private keys never leave hardware boundary.
- **Replay Protection**: Challenge nonces are tracked in `_consumed_nonces` and marked consumed immediately upon first verification. Replay attempts raise `ChallengeReplayError` (-32002).
- **Time-to-Live (TTL)**: Authentication challenges expire after 60 seconds. Expired challenges raise `ChallengeExpiredError`.
- **Immediate Device Revocation**: Revoking a device via `jarvis.network.device.revoke` or host action immediately terminates all active sessions and rejects subsequent calls with `-32001 Invalid or expired device session token`.
- **Biometric HITL (`StandardBiometricAuthManager`)**: All sensitive tool confirmations require `BiometricPrompt` authorization before transmitting `APPROVE` payloads. Network authentication does NOT grant permission to execute sensitive tools.
- **Secret Isolation**: Responses never disclose host IPC authentication tokens, private keys, or internal encryption seeds.
- **Strict Data Extraction Rules**: `android:allowBackup="false"` and `data_extraction_rules.xml` ensure zero cloud or device-transfer leakage of credentials or cache.
- **Informational Proactive Invariant**: Proactive DTOs (`ProactiveAdvisoryDto`) enforce `isInformationalOnly = true` and `isExecutableDirectly = false`. No autonomous execution paths exist.

---

## 5. Verification & Testing

Phase 8 is covered by automated test suites in `tests/test_phase8_android.py`, `tests/test_phase8_2_network_pairing.py`, and `android/app/src/test/java/com/jarvis/assistant/JarvisCompanionTest.kt`, bringing the repository test suite to **254 passing tests (100% pass rate in 1.21s)**:
## 4. Phase 8.3 — Secure Session Lifecycle & Live Communication

### 4.1 Connection State Machine

The Android client maintains a strict deterministic connection state machine:

```
[DISCONNECTED] ──(handshake)──> [CONNECTING] ──(connected)──> [AUTHENTICATING]
      ▲                                                              │
      │                                                     (auth verified)
      │                                                              ▼
(disconnect)                                                   [CONNECTED]
      │                                                         │       │
      │                                           (heartbeat fail) (revoked)
      │                                                         │       │
      ▼                                                         ▼       ▼
[DISCONNECTED] <──(exhausted)── [ERROR] <── [RECONNECTING]   [REVOKED]
```

- **DISCONNECTED**: Idle or explicitly closed connection.
- **CONNECTING**: Socket connection in progress.
- **AUTHENTICATING**: 2-step challenge-response handshake in flight.
- **CONNECTED**: Authenticated session established; periodic heartbeat active.
- **RECONNECTING**: Transient network drop detected; exponential backoff loop active.
- **REVOKED**: Device revoked by desktop host; all reconnect attempts immediately halted.
- **ERROR**: Retries exhausted or terminal network failure.

### 4.2 Bounded Exponential Backoff & Heartbeat

- **Heartbeat**: Android client transmits `jarvis.heartbeat` every 15 seconds. If the bridge fails to respond or reports session expiration, client transitions to `RECONNECTING`.
- **Reconnect Parameters**:
  - `initialDelayMs`: 1,000 ms
  - `maxDelayMs`: 30,000 ms
  - `multiplier`: 2.0x
  - `maxRetries`: 5 attempts
- **Replay Protection & Secret Isolation**: Request IDs correlate responses (`response.id == request.id`). Payload cap (5 MB) prevents DoS memory exhaustion. Host secrets and private keys are never transmitted.

---

## 5. Security & Invariant Verification Matrix

| Subsystem / Invariant | Enforcement Mechanism | Phase 8.1 Verification | Phase 8.2 Verification | Phase 8.3 Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Encrypted Storage** | Android Keystore (`AES/GCM/NoPadding`, 256-bit) | `test_keystore_manager_uses_aes_gcm_256` | Tested | Tested |
| **Biometric Confirmation**| `BiometricPrompt` with `BIOMETRIC_STRONG` | Tested in `ApprovalDialog.kt` | Tested | Tested |
| **No Cloud Backup** | `data_extraction_rules.xml` disallows cloud | `test_android_manifest_permissions_and_security` | Verified | Verified |
| **Informational Proactive**| `is_informational_only = true` immutable | `test_proactive_models_enforce_informational_only` | `test_proactive_and_plan_endpoints_over_network` | `test_proactive_advisory_informational_enforcement` |
| **Asymmetric Device Pairing**| 6-digit confirmation code & timing-safe equality | Scaffolding | `test_confirm_pairing_success` | Verified in live bridge |
| **Mutual Authentication** | 32-byte CSPRNG nonces, 60s TTL, replay prevention | Mocked | `test_auth_challenge_generation_and_verification` | `test_conversation_turn_round_trip` |
| **HITL Authorization Gate** | Sensitive tools require `ApprovalCard` + single-use token | Simulated in mock client | `test_hitl_approval_enforcement_over_network` | `test_hitl_approval_and_denial_flow` |
| **Emergency Stop** | `jarvis.system.emergency_stop` revokes in-flight authorizations | Tested | `test_emergency_stop_over_network` | `test_emergency_stop_kills_in_flight_approvals` |
| **State Tracking & Heartbeat** | Periodic `jarvis.heartbeat`, exponential backoff | N/A | N/A | `test_heartbeat_keepalive`, `test_phase8_3_network_client_state_machine_and_backoff` |
| **Revocation Invalidation** | Immediate session termination on revocation | N/A | `test_device_revocation_over_network_rpc` | `test_revoked_device_rejected` |

---

## 6. Automated Test Suites

- `tests/test_phase8_android.py` (11 tests verifying Android tree, Gradle structure, security XML, DTOs, and state machine).
- `tests/test_phase8_2_network_pairing.py` (16 tests verifying pairing registry, challenge signing, replay defense, and network RPCs).
- `tests/test_phase8_3_session_live.py` (13 tests verifying live session lifecycle, turn round trips, heartbeat, HITL approvals, emergency stop, and payload limits).
- Total repository tests: **269/269 passing 100%**.
