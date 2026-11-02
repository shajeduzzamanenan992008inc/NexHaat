package com.nexhaat.app.data.biometric

import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.nexhaat.app.R
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BiometricPromptHelper @Inject constructor(
    @ApplicationContext private val context: Context,
    private val biometricStorage: BiometricStorage
) {
    val authenticators = BIOMETRIC_STRONG or BIOMETRIC_WEAK

    fun getBiometricStatus(): BiometricAuthStatus {
        val manager = BiometricManager.from(context)
        return when (manager.canAuthenticate(authenticators)) {
            BiometricManager.BIOMETRIC_SUCCESS -> BiometricAuthStatus.Ready
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> BiometricAuthStatus.NoneEnrolled
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> BiometricAuthStatus.NotAvailable
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> BiometricAuthStatus.HardwareUnavailable
            else -> BiometricAuthStatus.NotAvailable
        }
    }

    fun canUseBiometricSignIn(): Boolean {
        return getBiometricStatus() is BiometricAuthStatus.Ready &&
            biometricStorage.isBiometricEnabled() &&
            !biometricStorage.getSavedEmail().isNullOrBlank() &&
            !biometricStorage.getSavedSecret().isNullOrBlank()
    }

    fun showBiometricPrompt(
        activity: FragmentActivity,
        title: String = activity.getString(R.string.biometric_prompt_title),
        subtitle: String = activity.getString(R.string.biometric_prompt_subtitle),
        description: String = activity.getString(R.string.biometric_prompt_description),
        negativeButtonText: String = activity.getString(R.string.cancel),
        onSuccess: () -> Unit,
        onError: (biometricError: BiometricError) -> Unit,
        onFailed: () -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)
        val prompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onSuccess()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    val error = BiometricError.fromErrorCode(errorCode, errString)
                    onError(error)
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    onFailed()
                }
            }
        )

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setDescription(description)
            .setNegativeButtonText(negativeButtonText)
            .setAllowedAuthenticators(authenticators)
            .build()

        prompt.authenticate(promptInfo)
    }

    fun openBiometricEnrollment(targetContext: Context = context) {
        val enrollIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Intent(Settings.ACTION_BIOMETRIC_ENROLL).apply {
                putExtra(Settings.EXTRA_BIOMETRIC_AUTHENTICATORS_ALLOWED, authenticators)
            }
        } else {
            Intent(Settings.ACTION_SECURITY_SETTINGS)
        }
        enrollIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        try {
            targetContext.startActivity(enrollIntent)
        } catch (_: Exception) {
            try {
                targetContext.startActivity(Intent(Settings.ACTION_SETTINGS).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                })
            } catch (_: Exception) {
                // Ignore device settings launch exceptions
            }
        }
    }
}
