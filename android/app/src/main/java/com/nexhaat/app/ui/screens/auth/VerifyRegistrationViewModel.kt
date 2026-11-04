package com.nexhaat.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class VerifyRegistrationUiState(
    val email: String = "",
    val challengeId: String? = null,
    val code: String = "",
    val isLoading: Boolean = false,
    val error: String? = null,
    val isVerified: Boolean = false,
    val resendCountdown: Int = 60
)

@HiltViewModel
class VerifyRegistrationViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(VerifyRegistrationUiState())
    val uiState: StateFlow<VerifyRegistrationUiState> = _uiState.asStateFlow()

    init {
        startCountdown()
    }

    fun initData(email: String, challengeId: String?) {
        _uiState.value = _uiState.value.copy(email = email, challengeId = challengeId)
    }

    fun setCode(value: String) {
        val filtered = value.filter { it.isDigit() }.take(6)
        _uiState.value = _uiState.value.copy(code = filtered, error = null)
        if (filtered.length == 6) {
            verifyCode(filtered)
        }
    }

    fun verifyCode(code: String = _uiState.value.code) {
        val state = _uiState.value
        if (state.isLoading) return
        if (code.length != 6) {
            _uiState.value = state.copy(error = "Please enter the complete 6-digit code.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = authRepository.verifyRegistration(
                code = code
            )) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isVerified = true,
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

    fun resendCode() {
        if (_uiState.value.resendCountdown > 0) return
        startCountdown()
        // In real backend, re-triggers register or OTP endpoint
    }

    private fun startCountdown() {
        _uiState.value = _uiState.value.copy(resendCountdown = 60)
        viewModelScope.launch {
            while (_uiState.value.resendCountdown > 0) {
                delay(1000)
                _uiState.value = _uiState.value.copy(resendCountdown = _uiState.value.resendCountdown - 1)
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
