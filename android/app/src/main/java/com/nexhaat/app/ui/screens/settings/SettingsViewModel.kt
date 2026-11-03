package com.nexhaat.app.ui.screens.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricError
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.repository.AuthRepository
import com.nexhaat.app.data.session.SessionManager
import com.nexhaat.app.data.session.SessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val isBiometricEnabled: Boolean = false,
    val biometricStatus: BiometricAuthStatus = BiometricAuthStatus.NotAvailable,
    val isAuthenticated: Boolean = false,
    val userNotice: String? = null
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val biometricPromptHelper: BiometricPromptHelper,
    private val biometricStorage: BiometricStorage,
    private val authRepository: AuthRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    val biometricHelper: BiometricPromptHelper
        get() = biometricPromptHelper

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            sessionManager.state.collect { refreshState() }
        }
    }

    fun refreshState() {
        val user = (sessionManager.state.value as? SessionState.Authenticated)?.user
        _uiState.value = _uiState.value.copy(
            isBiometricEnabled = user?.let { biometricStorage.isBiometricEnabledForUser(it.id) } ?: false,
            biometricStatus = biometricPromptHelper.getBiometricStatus(),
            isAuthenticated = user != null
        )
    }

    fun setBiometricEnabled(enabled: Boolean) {
        val user = (sessionManager.state.value as? SessionState.Authenticated)?.user
        if (user == null) {
            _uiState.value = _uiState.value.copy(
                isBiometricEnabled = false,
                isAuthenticated = false,
                userNotice = "Sign in before enabling biometric session unlock."
            )
            return
        }
        if (enabled && biometricPromptHelper.getBiometricStatus() !is BiometricAuthStatus.Ready) {
            _uiState.value = _uiState.value.copy(
                isBiometricEnabled = false,
                userNotice = "Biometrics are not available on this device."
            )
            return
        }
        if (!sessionManager.setBiometricPreference(user.id, enabled)) {
            refreshState()
            _uiState.value = _uiState.value.copy(
                userNotice = "Your session changed. Sign in again before changing biometric settings."
            )
            return
        }
        _uiState.value = _uiState.value.copy(
            isBiometricEnabled = enabled,
            isAuthenticated = true,
            userNotice = if (enabled) {
                "Biometric unlock is enabled for this account on this device."
            } else {
                "Biometric unlock is disabled."
            }
        )
    }

    fun revalidateBiometricSession() {
        val expectedUser = (sessionManager.state.value as? SessionState.Authenticated)?.user
        if (expectedUser == null || !biometricStorage.isBiometricEnabledForUser(expectedUser.id)) {
            _uiState.value = _uiState.value.copy(
                userNotice = "There is no active biometric-enabled session to verify."
            )
            refreshState()
            return
        }
        viewModelScope.launch {
            when (val result = authRepository.revalidateSession(expectedUser.id)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isBiometricEnabled = true,
                        isAuthenticated = true,
                        userNotice = "The active server session was verified."
                    )
                }
                is NetworkResult.Error -> {
                    refreshState()
                    _uiState.value = _uiState.value.copy(userNotice = result.message)
                }
                NetworkResult.Loading -> Unit
            }
        }
    }

    fun clearStoredBiometricData() {
        biometricStorage.clearBiometricPreference()
        _uiState.value = _uiState.value.copy(
            isBiometricEnabled = false,
            userNotice = "Biometric session unlock was disabled."
        )
    }

    fun onBiometricError(error: BiometricError) {
        refreshState()
        if (error !is BiometricError.UserCanceled) {
            _uiState.value = _uiState.value.copy(userNotice = error.message)
        }
    }

    fun openSystemBiometricSettings(context: android.content.Context) {
        biometricPromptHelper.openBiometricEnrollment(context)
    }

    fun dismissNotice() {
        _uiState.value = _uiState.value.copy(userNotice = null)
    }
}
