package com.nexhaat.app.data.biometric

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.biometric.BiometricPrompt
import java.io.IOException
import java.security.GeneralSecurityException
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BiometricSessionCrypto @Inject constructor(
    private val biometricStorage: BiometricStorage
) {
    fun createPromptCryptoObject(): BiometricPrompt.CryptoObject {
        val key = loadKeyStore().getKey(KEY_ALIAS, null) as? SecretKey
            ?: throw BiometricSessionKeyMissingException()
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.ENCRYPT_MODE, key)
        }
        return BiometricPrompt.CryptoObject(cipher)
    }

    fun prepareKeyForEnrollment() {
        loadKeyStore().deleteEntry(KEY_ALIAS)
        createKey()
    }

    fun completeAuthenticatedOperation(cipher: Cipher?): Boolean {
        if (cipher == null) return false
        cipher.doFinal(CHALLENGE)
        return true
    }

    fun disableAfterEnrollmentChange() {
        biometricStorage.clearBiometricPreference()
        try {
            loadKeyStore().deleteEntry(KEY_ALIAS)
        } catch (_: GeneralSecurityException) {
            // The invalidated key cannot authorize an operation; the preference is already disabled.
        } catch (_: IOException) {
            // The invalidated key cannot authorize an operation; the preference is already disabled.
        } catch (_: SecurityException) {
            // The invalidated key cannot authorize an operation; the preference is already disabled.
        }
    }

    private fun loadKeyStore(): KeyStore =
        KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }

    private fun createKey(): SecretKey {
        val builder = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            builder.setUserAuthenticationParameters(
                0,
                KeyProperties.AUTH_BIOMETRIC_STRONG
            )
        } else {
            builder.setUserAuthenticationValidityDurationSeconds(-1)
        }

        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEY_STORE).apply {
            init(builder.build())
        }.generateKey()
    }

    companion object {
        private const val ANDROID_KEY_STORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "nexhaat_biometric_session_key"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private val CHALLENGE = ByteArray(32) { index -> index.toByte() }
    }
}

class BiometricSessionKeyMissingException : GeneralSecurityException()
