package com.nexhaat.app.ui.screens.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.TotpSetupDto
import com.nexhaat.app.data.repository.AuthRepository
import com.nexhaat.app.data.session.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SecuritySettingsUiState(
    val isTotpEnabled: Boolean = false,
    val totpSetupData: TotpSetupDto? = null,
    val isSettingUpTotp: Boolean = false,
    val verificationCode: String = "",
    val backupCodes: List<String> = emptyList(),
    val isBiometricSupported: Boolean = false,
    val isBiometricEnabled: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null
)

@HiltViewModel
class SecuritySettingsViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val biometricPromptHelper: BiometricPromptHelper,
    private val biometricStorage: BiometricStorage,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        SecuritySettingsUiState(
            isBiometricSupported = biometricPromptHelper.getBiometricStatus() is BiometricAuthStatus.Ready,
            isBiometricEnabled = biometricStorage.isBiometricEnabled()
        )
    )
    val uiState: StateFlow<SecuritySettingsUiState> = _uiState.asStateFlow()

    fun setVerificationCode(code: String) {
        val filtered = code.filter { it.isDigit() }.take(6)
        _uiState.value = _uiState.value.copy(verificationCode = filtered, error = null)
    }

    fun startTotpSetup() {
        if (_uiState.value.isLoading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.setupTotp()) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        totpSetupData = result.data,
                        backupCodes = result.data.backupCodes,
                        isSettingUpTotp = true,
                        error = null
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message
                    )
                }
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    fun verifyTotp() {
        val state = _uiState.value
        if (state.isLoading) return
        if (state.verificationCode.length != 6) {
            _uiState.value = state.copy(error = "Please enter the 6-digit code from your authenticator app.")
            return
        }

        val secret = state.totpSetupData?.secret ?: run {
            _uiState.value = state.copy(error = "TOTP setup session expired. Please start again.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.verifyTotp(state.verificationCode, secret)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isTotpEnabled = true,
                        isSettingUpTotp = false,
                        verificationCode = "",
                        successMessage = "Two-Factor Authentication (2FA) is now enabled!"
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message
                    )
                }
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    fun toggleBiometric(enabled: Boolean) {
        val userId = biometricStorage.getBiometricUserId() ?: 1
        if (enabled) {
            sessionManager.setBiometricPreference(userId, true)
            _uiState.value = _uiState.value.copy(isBiometricEnabled = true)
        } else {
            biometricStorage.clearBiometricPreference()
            _uiState.value = _uiState.value.copy(isBiometricEnabled = false)
        }
    }

    fun cancelTotpSetup() {
        _uiState.value = _uiState.value.copy(isSettingUpTotp = false, verificationCode = "", error = null)
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(error = null, successMessage = null)
    }
}
