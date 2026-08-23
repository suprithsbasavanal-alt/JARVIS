package com.jarvis.assistant.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Hardware-backed Android Keystore Manager for securing companion pairing tokens and encryption keys.
 */
interface KeystoreManager {
    fun generateOrGetMasterKey(): Boolean
    fun encryptSecret(plainText: String): Pair<ByteArray, ByteArray> // Pair<IV, Ciphertext>
    fun decryptSecret(iv: ByteArray, cipherText: ByteArray): String
}

class StandardKeystoreManager(
    private val keyAlias: String = "JARVIS_COMPANION_MASTER_KEY"
) : KeystoreManager {

    private val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    override fun generateOrGetMasterKey(): Boolean {
        return try {
            if (!keyStore.containsAlias(keyAlias)) {
                val keyGenerator = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES,
                    "AndroidKeyStore"
                )
                val keyGenParameterSpec = KeyGenParameterSpec.Builder(
                    keyAlias,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .setUserAuthenticationRequired(false) // Will be gated by BiometricPrompt on action
                    .build()

                keyGenerator.init(keyGenParameterSpec)
                keyGenerator.generateKey()
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    override fun encryptSecret(plainText: String): Pair<ByteArray, ByteArray> {
        val secretKey = (keyStore.getEntry(keyAlias, null) as? KeyStore.SecretKeyEntry)?.secretKey
            ?: throw IllegalStateException("Key alias not found in AndroidKeyStore")

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)
        val iv = cipher.iv
        val cipherText = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))
        return Pair(iv, cipherText)
    }

    override fun decryptSecret(iv: ByteArray, cipherText: ByteArray): String {
        val secretKey = (keyStore.getEntry(keyAlias, null) as? KeyStore.SecretKeyEntry)?.secretKey
            ?: throw IllegalStateException("Key alias not found in AndroidKeyStore")

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(128, iv)
        cipher.init(Cipher.DECRYPT_MODE, secretKey, spec)
        val plainBytes = cipher.doFinal(cipherText)
        return String(plainBytes, Charsets.UTF_8)
    }
}
