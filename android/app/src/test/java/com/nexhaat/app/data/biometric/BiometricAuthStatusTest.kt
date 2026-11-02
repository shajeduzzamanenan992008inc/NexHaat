package com.nexhaat.app.data.biometric

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BiometricAuthStatusTest {

    @Test
    fun biometricAuthStatus_hasExpectedInstances() {
        val ready: BiometricAuthStatus = BiometricAuthStatus.Ready
        val notAvailable: BiometricAuthStatus = BiometricAuthStatus.NotAvailable
        val noneEnrolled: BiometricAuthStatus = BiometricAuthStatus.NoneEnrolled
        val hwUnavailable: BiometricAuthStatus = BiometricAuthStatus.HardwareUnavailable

        assertTrue(ready is BiometricAuthStatus.Ready)
        assertTrue(notAvailable is BiometricAuthStatus.NotAvailable)
        assertTrue(noneEnrolled is BiometricAuthStatus.NoneEnrolled)
        assertTrue(hwUnavailable is BiometricAuthStatus.HardwareUnavailable)
    }

    @Test
    fun biometricAuthStatus_equalityWorks() {
        assertEquals(BiometricAuthStatus.Ready, BiometricAuthStatus.Ready)
        assertEquals(BiometricAuthStatus.NoneEnrolled, BiometricAuthStatus.NoneEnrolled)
    }
}
