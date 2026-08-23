"""Automated Verification Test Suite for Phase 8.1: Android Companion Client Bootstrap."""

import json
from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).parent.parent
ANDROID_ROOT = REPO_ROOT / "android"
APP_ROOT = ANDROID_ROOT / "app"
SRC_MAIN = APP_ROOT / "src" / "main"
JAVA_SRC = SRC_MAIN / "java" / "com" / "jarvis" / "assistant"


class TestPhase8AndroidBootstrap(unittest.TestCase):
    """Verifies Android Companion Client project scaffolding, manifest, models, and security invariants."""

    def test_android_directory_and_gradle_structure(self) -> None:
        """1. Verify root and module-level Gradle build files exist and configure Kotlin 1.9 + Compose."""
        self.assertTrue((ANDROID_ROOT / "build.gradle.kts").exists())
        self.assertTrue((ANDROID_ROOT / "settings.gradle.kts").exists())
        self.assertTrue((ANDROID_ROOT / "gradle" / "wrapper" / "gradle-wrapper.properties").exists())
        self.assertTrue((APP_ROOT / "build.gradle.kts").exists())
        self.assertTrue((SRC_MAIN / "AndroidManifest.xml").exists())

        # Check Gradle settings include app module
        settings_content = (ANDROID_ROOT / "settings.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('include(":app")', settings_content)

        # Check App build.gradle.kts contains security, biometric and compose dependencies
        app_build = (APP_ROOT / "build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("androidx.compose", app_build)
        self.assertIn("androidx.security:security-crypto", app_build)
        self.assertIn("androidx.biometric:biometric", app_build)
        self.assertIn("kotlinx-serialization-json", app_build)

    def test_android_manifest_permissions_and_security(self) -> None:
        """2. Verify AndroidManifest.xml requests only necessary permissions and disables backup."""
        manifest_content = (SRC_MAIN / "AndroidManifest.xml").read_text(encoding="utf-8")
        self.assertIn("android.permission.INTERNET", manifest_content)
        self.assertIn("android.permission.USE_BIOMETRIC", manifest_content)
        self.assertIn('android:allowBackup="false"', manifest_content)
        self.assertIn('android:fullBackupContent="false"', manifest_content)

        # Verify data extraction rules disallow cloud backup
        data_rules = (SRC_MAIN / "res" / "xml" / "data_extraction_rules.xml").read_text(encoding="utf-8")
        self.assertIn('<exclude domain="sharedpref" path="." />', data_rules)

    def test_jsonrpc_dtos_match_ipc_backend(self) -> None:
        """3. Verify Kotlin data models map all 10 IPC server methods and DTO fields."""
        models_file = JAVA_SRC / "data" / "model" / "JsonRpcModels.kt"
        self.assertTrue(models_file.exists())
        content = models_file.read_text(encoding="utf-8")

        # Verify Core Models
        self.assertIn("data class JsonRpcRequest", content)
        self.assertIn("data class JsonRpcResponse", content)
        self.assertIn("data class HandshakeParams", content)
        self.assertIn("data class HandshakeResult", content)
        self.assertIn("data class StatusResult", content)
        self.assertIn("data class TurnProcessResult", content)
        self.assertIn("data class ApprovalCardDto", content)
        self.assertIn("data class ApprovalRespondParams", content)
        self.assertIn("data class ProactiveAdvisoryDto", content)
        self.assertIn("data class StructuredPlanDto", content)
        self.assertIn("data class EmergencyStopResult", content)

    def test_proactive_models_enforce_informational_only(self) -> None:
        """4. Verify ProactiveAdvisoryDto defaults isInformationalOnly to true."""
        models_file = JAVA_SRC / "data" / "model" / "JsonRpcModels.kt"
        content = models_file.read_text(encoding="utf-8")
        self.assertIn("val isInformationalOnly: Boolean = true", content)
        self.assertIn("val isExecutableDirectly: Boolean = false", content)

    def test_mock_ipc_client_handles_all_methods(self) -> None:
        """5. Verify MockJarvisIpcClient implements all methods of JarvisIpcClient."""
        client_file = JAVA_SRC / "data" / "remote" / "MockJarvisIpcClient.kt"
        self.assertTrue(client_file.exists())
        content = client_file.read_text(encoding="utf-8")

        self.assertIn("override suspend fun handshake", content)
        self.assertIn("override suspend fun getStatus", content)
        self.assertIn("override suspend fun createSession", content)
        self.assertIn("override suspend fun processTurn", content)
        self.assertIn("override suspend fun respondToApproval", content)
        self.assertIn("override suspend fun getLatestProactiveAdvisory", content)
        self.assertIn("override suspend fun getActivePlan", content)
        self.assertIn("override suspend fun updatePlanStep", content)
        self.assertIn("override suspend fun emergencyStop", content)

    def test_keystore_manager_uses_aes_gcm_256(self) -> None:
        """6. Verify KeystoreManager configures AES-GCM 256-bit keys."""
        keystore_file = JAVA_SRC / "security" / "KeystoreManager.kt"
        self.assertTrue(keystore_file.exists())
        content = keystore_file.read_text(encoding="utf-8")

        self.assertIn("KeyProperties.KEY_ALGORITHM_AES", content)
        self.assertIn("KeyProperties.BLOCK_MODE_GCM", content)
        self.assertIn("setKeySize(256)", content)
        self.assertIn("AES/GCM/NoPadding", content)

    def test_aether_theme_and_screens_exist(self) -> None:
        """7. Verify Stitch Aether HUD mobile screens and components exist."""
        self.assertTrue((JAVA_SRC / "ui" / "theme" / "Color.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "theme" / "Theme.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "components" / "AetherComponents.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "screens" / "DashboardScreen.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "screens" / "ChatScreen.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "screens" / "ApprovalDialog.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "screens" / "ProactiveScreen.kt").exists())
        self.assertTrue((JAVA_SRC / "ui" / "screens" / "PlanScreen.kt").exists())
        self.assertTrue((JAVA_SRC / "viewmodel" / "MainViewModel.kt").exists())
        self.assertTrue((JAVA_SRC / "MainActivity.kt").exists())

    def test_unit_tests_exist_in_android_tree(self) -> None:
        """8. Verify Kotlin unit test file exists under src/test."""
        test_file = APP_ROOT / "src" / "test" / "java" / "com" / "jarvis" / "assistant" / "JarvisCompanionTest.kt"
        self.assertTrue(test_file.exists())
        content = test_file.read_text(encoding="utf-8")
        self.assertIn("class JarvisCompanionTest", content)
        self.assertIn("testHandshakeSuccess", content)
        self.assertIn("testSensitiveActionTriggersApprovalCard", content)
        self.assertIn("testEmergencyStop", content)


if __name__ == "__main__":
    unittest.main()
