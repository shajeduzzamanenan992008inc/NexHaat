package com.nexhaat.app.data.session

import com.nexhaat.app.data.biometric.BiometricSessionCrypto
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.remote.interceptor.CsrfInterceptor
import com.nexhaat.app.data.remote.interceptor.PersistentCookieJar
import java.io.IOException
import java.security.GeneralSecurityException
import java.security.ProviderException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionManager @Inject constructor(
    private val cookieJar: PersistentCookieJar,
    private val csrfInterceptor: CsrfInterceptor,
    private val biometricStorage: BiometricStorage,
    private val biometricSessionCrypto: BiometricSessionCrypto
) {
    private val _state = MutableStateFlow<SessionState>(SessionState.Unknown)
    val state: StateFlow<SessionState> = _state.asStateFlow()

    @Synchronized
    fun authenticate(user: UserDto) {
        _state.value = SessionState.Authenticated(user)
    }

    @Synchronized
    fun setBiometricPreference(userId: Int, enabled: Boolean): Boolean {
        val activeUser = (_state.value as? SessionState.Authenticated)?.user
        if (activeUser?.id != userId) return false
        if (enabled) {
            try {
                biometricSessionCrypto.prepareKeyForEnrollment()
            } catch (_: GeneralSecurityException) {
                biometricStorage.clearBiometricPreference()
                return false
            } catch (_: IOException) {
                biometricStorage.clearBiometricPreference()
                return false
            } catch (_: SecurityException) {
                biometricStorage.clearBiometricPreference()
                return false
            } catch (_: ProviderException) {
                biometricStorage.clearBiometricPreference()
                return false
            }
        }
        biometricStorage.setBiometricEnabled(userId, enabled)
        return if (enabled) {
            biometricStorage.isBiometricEnabledForUser(userId)
        } else {
            !biometricStorage.isBiometricEnabled()
        }
    }

    @Synchronized
    fun clearSession() {
        cookieJar.clear()
        csrfInterceptor.clearCsrfToken()
        biometricStorage.clearBiometricPreference()
        _state.value = SessionState.Unauthenticated
    }
}
