package com.nexhaat.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.RegistrationChallengeDto
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SignUpUiState(
    val fullName: String = "",
    val email: String = "",
    val phone: String = "",
    val role: String = "customer",
    val password: String = "",
    val confirmPassword: String = "",
    val isLoading: Boolean = false,
    val error: String? = null,
    val challenge: RegistrationChallengeDto? = null,
    val signedInUser: UserDto? = null
)

@HiltViewModel
class SignUpViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SignUpUiState())
    val uiState: StateFlow<SignUpUiState> = _uiState.asStateFlow()

    fun setFullName(value: String) {
        _uiState.value = _uiState.value.copy(fullName = value, error = null)
    }

    fun setEmail(value: String) {
        _uiState.value = _uiState.value.copy(email = value, error = null)
    }

    fun setPhone(value: String) {
        _uiState.value = _uiState.value.copy(phone = value, error = null)
    }

    fun setRole(value: String) {
        _uiState.value = _uiState.value.copy(role = value)
    }

    fun setPassword(value: String) {
        _uiState.value = _uiState.value.copy(password = value, error = null)
    }

    fun setConfirmPassword(value: String) {
        _uiState.value = _uiState.value.copy(confirmPassword = value, error = null)
    }

    fun register() {
        val state = _uiState.value
        if (state.isLoading) return

        if (state.fullName.isBlank() || state.email.isBlank() || state.password.isBlank()) {
            _uiState.value = state.copy(error = "Please fill in all required fields.")
            return
        }

        if (state.password.length < 8) {
            _uiState.value = state.copy(error = "Password must be at least 8 characters long.")
            return
        }

        if (state.password != state.confirmPassword) {
            _uiState.value = state.copy(error = "Passwords do not match.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.register(
                fullName = state.fullName.trim(),
                email = state.email.trim(),
                password = state.password,
                role = state.role,
                phone = state.phone.trim().takeIf(String::isNotEmpty)
            )) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        challenge = result.data,
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

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
