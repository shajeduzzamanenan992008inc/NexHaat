package com.nexhaat.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.repository.AuthRepository
import com.nexhaat.app.data.session.SessionManager
import com.nexhaat.app.data.session.SessionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    sessionManager: SessionManager
) : ViewModel() {
    val sessionState: StateFlow<SessionState> = sessionManager.state

    private val _isLoggingOut = MutableStateFlow(false)
    val isLoggingOut: StateFlow<Boolean> = _isLoggingOut.asStateFlow()

    private val _logoutError = MutableStateFlow<String?>(null)
    val logoutError: StateFlow<String?> = _logoutError.asStateFlow()

    fun revalidateSession() {
        viewModelScope.launch {
            authRepository.revalidateSession()
        }
    }

    fun logout() {
        if (_isLoggingOut.value) return
        viewModelScope.launch {
            _isLoggingOut.value = true
            _logoutError.value = null
            try {
                when (val result = authRepository.logout()) {
                    is NetworkResult.Success -> Unit
                    is NetworkResult.Error -> _logoutError.value = result.message
                    NetworkResult.Loading -> Unit
                }
            } finally {
                _isLoggingOut.value = false
            }
        }
    }

    fun dismissLogoutError() {
        _logoutError.value = null
    }
}
