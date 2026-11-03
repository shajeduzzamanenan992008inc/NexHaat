package com.nexhaat.app.ui.screens.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.NotificationItemDto
import com.nexhaat.app.data.repository.NotificationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface NotificationsUiState {
    object Loading : NotificationsUiState
    data class Success(
        val unreadCount: Int,
        val notifications: List<NotificationItemDto>
    ) : NotificationsUiState
    data class Error(val message: String) : NotificationsUiState
}

@HiltViewModel
class NotificationsViewModel @Inject constructor(
    private val notificationRepository: NotificationRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<NotificationsUiState>(NotificationsUiState.Loading)
    val uiState: StateFlow<NotificationsUiState> = _uiState.asStateFlow()

    init {
        loadNotifications()
    }

    fun loadNotifications() {
        viewModelScope.launch {
            _uiState.value = NotificationsUiState.Loading
            when (val result = notificationRepository.getNotifications()) {
                is NetworkResult.Success -> {
                    _uiState.value = NotificationsUiState.Success(
                        unreadCount = result.data.unread,
                        notifications = result.data.notifications
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = NotificationsUiState.Error(result.message)
                }
            }
        }
    }

    fun markAllRead() {
        viewModelScope.launch {
            val result = notificationRepository.markAllRead()
            if (result is NetworkResult.Success) {
                loadNotifications()
            }
        }
    }

    fun markRead(id: Int) {
        viewModelScope.launch {
            val result = notificationRepository.markRead(id)
            if (result is NetworkResult.Success) {
                loadNotifications()
            }
        }
    }
}
