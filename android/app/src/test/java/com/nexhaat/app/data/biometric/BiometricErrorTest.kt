package com.nexhaat.app.data.biometric

import androidx.biometric.BiometricPrompt
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BiometricErrorTest {

    @Test
    fun userCanceled_mapsToUserCanceled() {
        val error1 = BiometricError.fromErrorCode(BiometricPrompt.ERROR_USER_CANCELED, "Canceled")
        val error2 = BiometricError.fromErrorCode(BiometricPrompt.ERROR_NEGATIVE_BUTTON, "Cancel clicked")
        val error3 = BiometricError.fromErrorCode(BiometricPrompt.ERROR_CANCELED, "System canceled")

        assertEquals(BiometricError.UserCanceled, error1)
        assertEquals(BiometricError.UserCanceled, error2)
        assertEquals(BiometricError.UserCanceled, error3)
        assertFalse(error1.requiresFallbackPassword)
    }

    @Test
    fun enrollmentChangeAndCryptoFailure_requirePasswordSignIn() {
        assertTrue(BiometricError.EnrollmentChanged.requiresFallbackPassword)
        assertTrue(BiometricError.CryptoUnavailable.requiresFallbackPassword)
    }

    @Test
    fun lockout_mapsToTemporaryLockout() {
        val error = BiometricError.fromErrorCode(BiometricPrompt.ERROR_LOCKOUT, "Too many attempts")

        assertTrue(error is BiometricError.TemporaryLockout)
        assertTrue(error.requiresFallbackPassword)
        assertTrue(error.message.contains("temporarily locked"))
    }

    @Test
    fun permanentLockout_mapsToPermanentLockout() {
        val error = BiometricError.fromErrorCode(BiometricPrompt.ERROR_LOCKOUT_PERMANENT, "Permanently locked")

        assertTrue(error is BiometricError.PermanentLockout)
        assertTrue(error.requiresFallbackPassword)
        assertTrue(error.message.contains("permanently locked"))
    }

    @Test
    fun noBiometrics_mapsToNoneEnrolled() {
        val error = BiometricError.fromErrorCode(BiometricPrompt.ERROR_NO_BIOMETRICS, "None enrolled")

        assertTrue(error is BiometricError.NoneEnrolled)
        assertTrue(error.requiresFallbackPassword)
    }

    @Test
    fun hwUnavailable_mapsToHardwareUnavailable() {
        val error = BiometricError.fromErrorCode(BiometricPrompt.ERROR_HW_UNAVAILABLE, "Sensor busy")

        assertTrue(error is BiometricError.HardwareUnavailable)
        assertTrue(error.requiresFallbackPassword)
    }

    @Test
    fun unknownErrorCode_mapsToGeneric() {
        val error = BiometricError.fromErrorCode(999, "Custom sensor fault")

        assertTrue(error is BiometricError.Generic)
        val generic = error as BiometricError.Generic
        assertEquals(999, generic.errorCode)
        assertEquals("Custom sensor fault", generic.reason)
    }
}
