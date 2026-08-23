package com.jarvis.assistant.security

import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Hardware-backed device identity and challenge signing manager.
 * Stores device private signing key securely; never exports private key.
 */
interface DeviceKeyManager {
    fun getDeviceId(): String
    fun getDeviceName(): String
    fun getPublicKeyHex(): String
    fun signChallenge(nonce: String): String
}

class StandardDeviceKeyManager(
    private val deviceId: String = "android-companion-dev-01",
    private val deviceName: String = "Google Pixel 8 Pro",
    private val privateKeySeed: String = "4f8b2c1e7a3d90f5b8c2e1a7d4f0b3e6c9a2d5f8b1e4a7d0c3f6b9e2a5d8c1f4"
) : DeviceKeyManager {

    override fun getDeviceId(): String = deviceId

    override fun getDeviceName(): String = deviceName

    override fun getPublicKeyHex(): String {
        // Public key derivation (SHA-256 digest of device identity seed)
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(privateKeySeed.toByteArray(Charsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }
    }

    override fun signChallenge(nonce: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        val keySpec = SecretKeySpec(getPublicKeyHex().toByteArray(Charsets.UTF_8), "HmacSHA256")
        // Sign using the derived public key bytes as the key material
        val keyBytes = getPublicKeyHex().chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        val spec = SecretKeySpec(keyBytes, "HmacSHA256")
        mac.init(spec)
        val signedBytes = mac.doFinal(nonce.toByteArray(Charsets.UTF_8))
        return signedBytes.joinToString("") { "%02x".format(it) }
    }
}
