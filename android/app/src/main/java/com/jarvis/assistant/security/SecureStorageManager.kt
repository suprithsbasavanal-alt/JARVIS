package com.jarvis.assistant.security

import android.util.Base64
import java.util.concurrent.ConcurrentHashMap

/**
 * Secure Storage Manager encrypting sensitive tokens and pairing secrets
 * using Android Keystore (AES-GCM-256) without plaintext persistence.
 */
interface SecureStorageManager {
    fun saveSessionToken(sessionToken: String)
    fun getSessionToken(): String?
    fun clearSessionToken()
    fun savePairingKey(keyHex: String)
    fun getPairingKey(): String?
    fun wipeAllCredentials()
}

class StandardSecureStorageManager(
    private val keystoreManager: KeystoreManager = StandardKeystoreManager()
) : SecureStorageManager {

    private val memoryStore = ConcurrentHashMap<String, Pair<String, String>>() // Key -> Pair(Base64 IV, Base64 Ciphertext)

    init {
        keystoreManager.generateOrGetMasterKey()
    }

    override fun saveSessionToken(sessionToken: String) {
        if (sessionToken.isBlank()) return
        val (iv, cipher) = keystoreManager.encryptSecret(sessionToken)
        val ivB64 = Base64.encodeToString(iv, Base64.NO_WRAP)
        val cipherB64 = Base64.encodeToString(cipher, Base64.NO_WRAP)
        memoryStore["SESSION_TOKEN"] = Pair(ivB64, cipherB64)
    }

    override fun getSessionToken(): String? {
        val entry = memoryStore["SESSION_TOKEN"] ?: return null
        return try {
            val iv = Base64.decode(entry.first, Base64.NO_WRAP)
            val cipher = Base64.decode(entry.second, Base64.NO_WRAP)
            keystoreManager.decryptSecret(iv, cipher)
        } catch (e: Exception) {
            null
        }
    }

    override fun clearSessionToken() {
        memoryStore.remove("SESSION_TOKEN")
    }

    override fun savePairingKey(keyHex: String) {
        if (keyHex.isBlank()) return
        val (iv, cipher) = keystoreManager.encryptSecret(keyHex)
        val ivB64 = Base64.encodeToString(iv, Base64.NO_WRAP)
        val cipherB64 = Base64.encodeToString(cipher, Base64.NO_WRAP)
        memoryStore["PAIRING_KEY"] = Pair(ivB64, cipherB64)
    }

    override fun getPairingKey(): String? {
        val entry = memoryStore["PAIRING_KEY"] ?: return null
        return try {
            val iv = Base64.decode(entry.first, Base64.NO_WRAP)
            val cipher = Base64.decode(entry.second, Base64.NO_WRAP)
            keystoreManager.decryptSecret(iv, cipher)
        } catch (e: Exception) {
            null
        }
    }

    override fun wipeAllCredentials() {
        memoryStore.clear()
    }
}
