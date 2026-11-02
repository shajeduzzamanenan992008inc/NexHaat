package com.nexhaat.app.ui.screens.settings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val isBiometricEnabled: Boolean = false,
    val biometricStatus: BiometricAuthStatus = BiometricAuthStatus.NotAvailable,
    val savedEmail: String? = null,
    val fallbackPasswordInput: String = "",
    val isVerifyingFallback: Boolean = false,
    val fallbackVerifyResult: String? = null,
    val fallbackVerifyError: String? = null,
    val userNotice: String? = null
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val biometricPromptHelper: BiometricPromptHelper,
    private val biometricStorage: BiometricStorage,
    private val authRepository: AuthRepository
) : ViewModel() {

    val biometricHelper: BiometricPromptHelper
        get() = biometricPromptHelper

    private val _uiState = MutableStateFlow(

        SettingsUiState(
            isBiometricEnabled = biometricStorage.isBiometricEnabled(),
            biometricStatus = biometricPromptHelper.getBiometricStatus(),
            savedEmail = biometricStorage.getSavedEmail()
        )
    )
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    fun refreshState() {
        _uiState.value = _uiState.value.copy(
            isBiometricEnabled = biometricStorage.isBiometricEnabled(),
            biometricStatus = biometricPromptHelper.getBiometricStatus(),
            savedEmail = biometricStorage.getSavedEmail()
        )
    }

    fun setBiometricEnabled(enabled: Boolean) {
        if (!enabled) {
            biometricStorage.clearBiometricCredentials()
            _uiState.value = _uiState.value.copy(
                isBiometricEnabled = false,
                savedEmail = null,
                userNotice = "Biometric authentication disabled."
            )
        } else {
            // When enabling, requires saving credentials on next login or setting status
            _uiState.value = _uiState.value.copy(
                isBiometricEnabled = true,
                userNotice = "Biometric sign-in activated. Sign in to link your biometric credentials."
            )
        }
    }

    fun setFallbackPasswordInput(input: String) {
        _uiState.value = _uiState.value.copy(
            fallbackPasswordInput = input,
            fallbackVerifyError = null,
            fallbackVerifyResult = null
        )
    }

    fun verifyFallbackPassword(email: String) {
        val password = _uiState.value.fallbackPasswordInput
        if (password.isBlank()) {
            _uiState.value = _uiState.value.copy(fallbackVerifyError = "Enter your password to verify fallback.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isVerifyingFallback = true, fallbackVerifyError = null)
            when (val result = authRepository.login(email.trim(), password)) {
                is NetworkResult.Success -> {
                    // Update biometric storage with verified credentials
                    biometricStorage.saveBiometricCredentials(email.trim(), password)
                    _uiState.value = _uiState.value.copy(
                        isVerifyingFallback = false,
                        isBiometricEnabled = true,
                        savedEmail = email.trim(),
                        fallbackPasswordInput = "",
                        fallbackVerifyResult = "Fallback authentication verified successfully! Biometrics linked."
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isVerifyingFallback = false,
                        fallbackVerifyError = result.message
                    )
                }
                NetworkResult.Loading -> {
                    _uiState.value = _uiState.value.copy(isVerifyingFallback = false)
                }
            }
        }
    }

    fun clearStoredBiometricData() {
        biometricStorage.clearBiometricCredentials()
        _uiState.value = _uiState.value.copy(
            isBiometricEnabled = false,
            savedEmail = null,
            userNotice = "Stored biometric credentials cleared from device."
        )
    }

    fun openSystemBiometricSettings(context: Context) {
        biometricPromptHelper.openBiometricEnrollment(context)
    }

    fun dismissNotice() {
        _uiState.value = _uiState.value.copy(userNotice = null)
    }
}
