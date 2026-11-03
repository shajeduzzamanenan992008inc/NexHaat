package com.nexhaat.app.data.biometric

import androidx.biometric.BiometricPrompt

sealed class BiometricError(val message: String) {
    object UserCanceled : BiometricError("Authentication was canceled by user.")
    object EnrollmentChanged : BiometricError(
        "Biometric enrollment changed. Sign in with your password and enable biometric unlock again."
    )
    object SetupRequired : BiometricError(
        "Biometric setup needs refreshing. Sign in with your password and enable biometric unlock again."
    )
    object CryptoUnavailable : BiometricError(
        "Secure biometric verification is unavailable. Sign in with your password."
    )
    data class TemporaryLockout(val reason: String) : BiometricError(reason)
    data class PermanentLockout(val reason: String) : BiometricError(reason)
    data class NoneEnrolled(val reason: String) : BiometricError(reason)
    data class HardwareUnavailable(val reason: String) : BiometricError(reason)
    data class Generic(val errorCode: Int, val reason: String) : BiometricError(reason)

    val requiresFallbackPassword: Boolean
        get() = this is TemporaryLockout ||
            this is PermanentLockout ||
            this is NoneEnrolled ||
            this is HardwareUnavailable ||
            this is EnrollmentChanged ||
            this is SetupRequired ||
            this is CryptoUnavailable

    companion object {
        fun fromErrorCode(errorCode: Int, errString: CharSequence?): BiometricError {
            val defaultMsg = errString?.toString()?.takeIf { it.isNotBlank() } ?: "Authentication error ($errorCode)"
            return when (errorCode) {
                BiometricPrompt.ERROR_USER_CANCELED,
                BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                BiometricPrompt.ERROR_CANCELED -> UserCanceled

                BiometricPrompt.ERROR_LOCKOUT -> TemporaryLockout(
                    "Too many failed attempts. Biometric sensor is temporarily locked for 30 seconds. Please use your password."
                )

                BiometricPrompt.ERROR_LOCKOUT_PERMANENT -> PermanentLockout(
                    "Biometric sensor is permanently locked until you unlock with your device PIN or password."
                )

                BiometricPrompt.ERROR_NO_BIOMETRICS -> NoneEnrolled(
                    "No biometric enrolled. Please register a fingerprint or face unlock in system settings."
                )

                BiometricPrompt.ERROR_HW_NOT_PRESENT,
                BiometricPrompt.ERROR_HW_UNAVAILABLE -> HardwareUnavailable(
                    "Biometric hardware is not available on this device."
                )

                else -> Generic(errorCode, defaultMsg)
            }
        }
    }
}
