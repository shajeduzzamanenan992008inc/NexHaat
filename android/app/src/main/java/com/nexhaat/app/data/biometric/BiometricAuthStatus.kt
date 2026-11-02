package com.nexhaat.app.data.biometric

sealed class BiometricAuthStatus {
    object Ready : BiometricAuthStatus()
    object NotAvailable : BiometricAuthStatus()
    object NoneEnrolled : BiometricAuthStatus()
    object HardwareUnavailable : BiometricAuthStatus()
}
