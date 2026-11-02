package com.nexhaat.app.data.biometric

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BiometricStorage @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val masterKey by lazy {
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
    }

    private val sharedPreferences by lazy {
        EncryptedSharedPreferences.create(
            context,
            "nexhaat_biometric_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    fun saveBiometricCredentials(email: String, secret: String) {
        sharedPreferences.edit()
            .putString(KEY_EMAIL, email)
            .putString(KEY_SECRET, secret)
            .putBoolean(KEY_BIOMETRIC_ENABLED, true)
            .apply()
    }

    fun getSavedEmail(): String? = sharedPreferences.getString(KEY_EMAIL, null)

    fun getSavedSecret(): String? = sharedPreferences.getString(KEY_SECRET, null)

    fun isBiometricEnabled(): Boolean = sharedPreferences.getBoolean(KEY_BIOMETRIC_ENABLED, false)

    fun clearBiometricCredentials() {
        sharedPreferences.edit()
            .remove(KEY_EMAIL)
            .remove(KEY_SECRET)
            .putBoolean(KEY_BIOMETRIC_ENABLED, false)
            .apply()
    }

    companion object {
        private const val KEY_EMAIL = "key_biometric_email"
        private const val KEY_SECRET = "key_biometric_secret"
        private const val KEY_BIOMETRIC_ENABLED = "key_biometric_enabled"
    }
}
