# JARVIS Android Companion Client

> **Phase 0 — Safe Development Specification**

This directory houses the architectural design, security integration, and UI scaffolding for the **JARVIS Android Companion Client**.

---

## 1. Architecture Overview

The Android client is designed with native **Kotlin & Jetpack Compose**:
- **Hardware Keystore Integration**: Leverages Android Keystore (StrongBox Keymaster) to store device Ed25519 signing keys and decrypt incoming messages.
- **Biometric Authentication**: Enforces `BiometricPrompt` for approving `SENSITIVE` actions initiated from the mobile device.
- **Background Synchronization**: Uses `WorkManager` for scheduled, battery-efficient state synchronization over local network mTLS or encrypted relay.

---

## 2. Directory Scaffolding (Planned for Phase 8)

```
android/
├── README.md
├── build.gradle.kts
├── app/
│   ├── build.gradle.kts
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   └── java/com/jarvis/assistant/
│   │       ├── MainActivity.kt
│   │       ├── security/          # Keystore & Biometrics
│   │       ├── sync/              # mTLS & Network Sync
│   │       ├── ui/                # Jetpack Compose Screens
│   │       └── service/           # Notification & Audio Listener
```
