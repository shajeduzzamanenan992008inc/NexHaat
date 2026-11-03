package com.nexhaat.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricError
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.repository.AuthRepository
import com.nexhaat.app.data.session.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SignInUiState(
    val email: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val error: String? = null,
    val signedInUser: UserDto? = null,
    val canUseBiometric: Boolean = false,
    val isBiometricSupported: Boolean = false,
    val saveBiometricForFuture: Boolean = false
)

@HiltViewModel
class SignInViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val biometricPromptHelper: BiometricPromptHelper,
    private val biometricStorage: BiometricStorage,
    private val sessionManager: SessionManager
) : ViewModel() {
    private val _uiState = MutableStateFlow(
        SignInUiState(
            canUseBiometric = biometricStorage.isBiometricEnabled(),
            isBiometricSupported = biometricPromptHelper.getBiometricStatus() is BiometricAuthStatus.Ready
        )
    )
    val uiState: StateFlow<SignInUiState> = _uiState.asStateFlow()

    fun setEmail(value: String) {
        _uiState.value = _uiState.value.copy(email = value, error = null)
    }

    fun setPassword(value: String) {
        _uiState.value = _uiState.value.copy(password = value, error = null)
    }

    fun setSaveBiometricForFuture(enabled: Boolean) {
        _uiState.value = _uiState.value.copy(saveBiometricForFuture = enabled)
    }

    fun signIn() {
        val state = _uiState.value
        if (state.isLoading) return
        if (state.email.isBlank() || state.password.isBlank()) {
            _uiState.value = state.copy(error = "Enter your email and password.")
            return
        }
        val cleanEmail = state.email.trim()
        val plainPassword = state.password
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.login(cleanEmail, plainPassword)) {
                is NetworkResult.Success -> {
                    val biometricEnabled = state.saveBiometricForFuture &&
                        _uiState.value.isBiometricSupported &&
                        sessionManager.setBiometricPreference(result.data.id, true)
                    if (!biometricEnabled) {
                        biometricStorage.clearBiometricPreference()
                    }
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        password = "",
                        signedInUser = result.data,
                        canUseBiometric = biometricStorage.isBiometricEnabledForUser(result.data.id),
                        error = if (state.saveBiometricForFuture && !biometricEnabled) {
                            "Biometric unlock could not be enabled. You can enable it later in Settings."
                        } else {
                            null
                        }
                    )
                }
                is NetworkResult.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = result.message
                )
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    fun socialLogin(provider: String, token: String, email: String, name: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.socialLogin(provider, token, email, name)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        signedInUser = result.data,
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

    val biometricHelper: BiometricPromptHelper
        get() = biometricPromptHelper

    fun revalidateBiometricSession() {
        if (!_uiState.value.canUseBiometric || _uiState.value.isLoading) return
        val expectedUserId = biometricStorage.getBiometricUserId() ?: run {
            biometricStorage.clearBiometricPreference()
            _uiState.value = _uiState.value.copy(
                canUseBiometric = false,
                error = "Biometric session is unavailable. Sign in with your password."
            )
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.revalidateSession(expectedUserId)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        signedInUser = result.data
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message,
                        canUseBiometric = biometricStorage.isBiometricEnabled()
                    )
                }
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    fun onBiometricError(error: BiometricError) {
        _uiState.value = _uiState.value.copy(
            canUseBiometric = biometricStorage.isBiometricEnabled(),
            error = if (error is BiometricError.UserCanceled) null else error.message
        )
    }


    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
