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
        ).also { preferences ->
            if (preferences.contains(KEY_EMAIL) || preferences.contains(KEY_SECRET)) {
                preferences.edit()
                    .remove(KEY_EMAIL)
                    .remove(KEY_SECRET)
                    .remove(KEY_BIOMETRIC_USER_ID)
                    .putBoolean(KEY_BIOMETRIC_ENABLED, false)
                    .apply()
            }
        }
    }

    fun setBiometricEnabled(userId: Int, enabled: Boolean) {
        if (!enabled || userId <= 0) {
            clearBiometricPreference()
            return
        }
        sharedPreferences.edit()
            .putInt(KEY_BIOMETRIC_USER_ID, userId)
            .putBoolean(KEY_BIOMETRIC_ENABLED, true)
            .apply()
    }

    fun isBiometricEnabled(): Boolean = sharedPreferences.getBoolean(KEY_BIOMETRIC_ENABLED, false)

    fun isBiometricEnabledForUser(userId: Int): Boolean =
        userId > 0 &&
            isBiometricEnabled() &&
            sharedPreferences.getInt(KEY_BIOMETRIC_USER_ID, INVALID_USER_ID) == userId

    fun getBiometricUserId(): Int? =
        sharedPreferences.getInt(KEY_BIOMETRIC_USER_ID, INVALID_USER_ID)
            .takeIf { it > 0 && isBiometricEnabled() }

    fun clearBiometricPreference() {
        sharedPreferences.edit()
            .remove(KEY_BIOMETRIC_USER_ID)
            .putBoolean(KEY_BIOMETRIC_ENABLED, false)
            .apply()
    }

    companion object {
        private const val INVALID_USER_ID = -1
        private const val KEY_EMAIL = "key_biometric_email"
        private const val KEY_SECRET = "key_biometric_secret"
        private const val KEY_BIOMETRIC_ENABLED = "key_biometric_enabled"
        private const val KEY_BIOMETRIC_USER_ID = "key_biometric_user_id"
    }
}
