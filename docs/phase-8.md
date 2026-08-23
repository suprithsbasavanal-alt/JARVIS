# Phase 8 — Android Companion Client

## 1. Overview & Architecture

Phase 8 introduces the native **Android Companion Client** for JARVIS, designed with **Kotlin & Jetpack Compose**. The Android app serves as an authoritative remote interface and companion HUD for the JARVIS host daemon, providing:

1. **Dashboard & Status**: Real-time agent status, health score gauge, and active session monitoring.
2. **Conversational Command Bar**: Submitting turns to the backend `AgentLoop` and receiving synthesized replies.
3. **Biometric Human-in-the-Loop (HITL) Gate**: Hardware-authenticated confirmation modal for sensitive/destructive tool executions via Android `BiometricPrompt`.
4. **Proactive Intelligence Drawer**: Continuous project review reports, security findings, and epistemic disagreement observations (strictly informational-only).
5. **Plan & Milestone Checklists**: Real-time progress synchronization with host `StructuredPlan` states.
6. **Emergency Stop**: Instant revocation of all active approval tokens and pending authorizations (`jarvis.system.emergency_stop`).

---

## 2. Directory Structure (`android/`)

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
        │       │   └── repository/JarvisRepository.kt
        │       ├── security/
        │       │   ├── KeystoreManager.kt
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
```

---

## 3. Security & Cryptographic Invariants

- **Hardware Keystore (`StandardKeystoreManager`)**: Configures AES-256-GCM hardware-backed keys (`AndroidKeyStore`) for securing companion tokens.
- **Biometric HITL (`StandardBiometricAuthManager`)**: All sensitive tool confirmations require `BiometricPrompt` authorization before transmitting `APPROVE` payloads.
- **Strict Data Extraction Rules**: `android:allowBackup="false"` and `data_extraction_rules.xml` ensure zero cloud or device-transfer leakage of credentials or cache.
- **Informational Proactive Invariant**: Proactive DTOs (`ProactiveAdvisoryDto`) enforce `isInformationalOnly = true` and `isExecutableDirectly = false`. No autonomous execution paths exist.

---

## 4. Verification & Testing

Phase 8.1 includes automated validation in `tests/test_phase8_android.py` and `android/app/src/test/java/com/jarvis/assistant/JarvisCompanionTest.kt`, bringing the repository test suite to **237 passing tests (100% pass rate in 1.23s)**:

- `test_android_directory_and_gradle_structure`: Validates Gradle scripts, plugins, and dependencies.
- `test_android_manifest_permissions_and_security`: Validates permissions, backup disabled, and extraction rules.
- `test_jsonrpc_dtos_match_ipc_backend`: Validates Kotlin DTO mapping for all 10 IPC server methods.
- `test_proactive_models_enforce_informational_only`: Validates informational-only defaults on proactive models.
- `test_mock_ipc_client_handles_all_methods`: Validates in-memory mock client implementation.
- `test_keystore_manager_uses_aes_gcm_256`: Validates AES-GCM 256-bit configuration in KeystoreManager.
- `test_aether_theme_and_screens_exist`: Validates Compose theme, components, and screens.
- `test_unit_tests_exist_in_android_tree`: Validates Kotlin unit test suite presence.
