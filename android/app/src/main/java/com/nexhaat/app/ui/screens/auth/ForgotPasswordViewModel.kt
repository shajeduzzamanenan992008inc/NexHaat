package com.nexhaat.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ForgotPasswordUiState(
    val email: String = "",
    val code: String = "",
    val newPassword: String = "",
    val confirmPassword: String = "",
    val codeSent: Boolean = false,
    val isResetSuccessful: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null
)

@HiltViewModel
class ForgotPasswordViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ForgotPasswordUiState())
    val uiState: StateFlow<ForgotPasswordUiState> = _uiState.asStateFlow()

    fun setEmail(value: String) {
        _uiState.value = _uiState.value.copy(email = value, error = null)
    }

    fun setCode(value: String) {
        val filtered = value.filter { it.isDigit() }.take(6)
        _uiState.value = _uiState.value.copy(code = filtered, error = null)
    }

    fun setNewPassword(value: String) {
        _uiState.value = _uiState.value.copy(newPassword = value, error = null)
    }

    fun setConfirmPassword(value: String) {
        _uiState.value = _uiState.value.copy(confirmPassword = value, error = null)
    }

    fun requestResetCode() {
        val state = _uiState.value
        if (state.isLoading) return
        if (state.email.isBlank()) {
            _uiState.value = state.copy(error = "Please enter your email address.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.forgotPassword(state.email.trim())) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        codeSent = true,
                        successMessage = "Verification code has been sent to your email."
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

    fun resetPassword() {
        val state = _uiState.value
        if (state.isLoading) return

        if (state.code.length != 6) {
            _uiState.value = state.copy(error = "Please enter the 6-digit verification code.")
            return
        }

        if (state.newPassword.length < 8) {
            _uiState.value = state.copy(error = "Password must be at least 8 characters long.")
            return
        }

        if (state.newPassword != state.confirmPassword) {
            _uiState.value = state.copy(error = "Passwords do not match.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.resetPassword(
                email = state.email.trim(),
                code = state.code.trim(),
                newPassword = state.newPassword
            )) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isResetSuccessful = true,
                        successMessage = "Password reset successfully! You can now sign in."
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

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
