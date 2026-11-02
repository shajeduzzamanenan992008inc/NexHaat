package com.nexhaat.app.ui.screens.auth

import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.biometric.BiometricAuthStatus
import com.nexhaat.app.data.biometric.BiometricPromptHelper
import com.nexhaat.app.data.biometric.BiometricStorage
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.repository.AuthRepository
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
    val saveBiometricForFuture: Boolean = true
)

@HiltViewModel
class SignInViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val biometricPromptHelper: BiometricPromptHelper,
    private val biometricStorage: BiometricStorage
) : ViewModel() {
    private val _uiState = MutableStateFlow(
        SignInUiState(
            email = biometricStorage.getSavedEmail() ?: "",
            canUseBiometric = biometricPromptHelper.canUseBiometricSignIn(),
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
                    if (state.saveBiometricForFuture && _uiState.value.isBiometricSupported) {
                        biometricStorage.saveBiometricCredentials(cleanEmail, plainPassword)
                    }
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        password = "",
                        signedInUser = result.data,
                        canUseBiometric = biometricPromptHelper.canUseBiometricSignIn()
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

    val biometricHelper: BiometricPromptHelper
        get() = biometricPromptHelper

    fun signInWithBiometric(activity: FragmentActivity, onError: ((BiometricError) -> Unit)? = null) {
        if (!_uiState.value.canUseBiometric) return
        val savedEmail = biometricStorage.getSavedEmail() ?: return
        val savedSecret = biometricStorage.getSavedSecret() ?: return

        biometricPromptHelper.showBiometricPrompt(
            activity = activity,
            onSuccess = {
                viewModelScope.launch {
                    _uiState.value = _uiState.value.copy(isLoading = true, error = null)
                    when (val result = authRepository.login(savedEmail, savedSecret)) {
                        is NetworkResult.Success -> _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            signedInUser = result.data
                        )
                        is NetworkResult.Error -> _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            error = result.message
                        )
                        NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
                    }
                }
            },
            onError = { biometricError ->
                if (biometricError !is BiometricError.UserCanceled) {
                    _uiState.value = _uiState.value.copy(error = biometricError.message)
                }
                onError?.invoke(biometricError)
            },
            onFailed = {
                _uiState.value = _uiState.value.copy(error = "Biometric authentication failed. Please try again or use your password.")
            }
        )
    }


    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
