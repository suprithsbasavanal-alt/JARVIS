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

- `TestPhase82DevicePairingRegistry`:
  - `test_begin_pairing_success`: Generates 6-digit code and creates `PENDING_CONFIRMATION` record.
  - `test_confirm_pairing_success`: Valid code transitions device to `CONFIRMED`.
  - `test_confirm_pairing_invalid_code_rejected`: Wrong code raises `InvalidPairingCodeError`.
  - `test_auth_challenge_generation_and_verification`: Nonce generation, signature verification, and session issuance.
  - `test_invalid_signature_rejected`: Bad signature raises `InvalidSignatureError`.
  - `test_challenge_replay_rejected`: Consumed nonce replay raises `ChallengeReplayError`.
  - `test_expired_challenge_rejected`: Expired TTL challenge raises `ChallengeExpiredError`.
  - `test_device_revocation_terminates_sessions`: Revocation terminates active sessions and blocks challenges.
  - `test_device_key_rotation_lifecycle`: Key rotation validates authorization signature and updates registry.
  - `test_list_devices`: Lists registered devices and lifecycle states.
- `TestPhase82NetworkBridgeIntegration`:
  - `test_unauthenticated_requests_rejected`: Unauthenticated RPC calls return `-32000 Authentication required`.
  - `test_complete_pairing_and_mutual_auth_flow`: End-to-end pairing, challenge signing, and turn execution.
  - `test_hitl_approval_enforcement_over_network`: Sensitive tools raise approval cards and require explicit `APPROVE`.
  - `test_emergency_stop_over_network`: Emergency stop over network revokes in-flight authorizations.
  - `test_device_revocation_over_network_rpc`: RPC revocation immediately terminates session token validity.
  - `test_proactive_and_plan_endpoints_over_network`: Informational proactive advisories and plan sync over network.
