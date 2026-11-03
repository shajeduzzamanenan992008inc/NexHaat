package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.NotificationListDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationRepository @Inject constructor(
    private val apiService: ApiService,
    private val authRepository: AuthRepository
) {
    suspend fun getNotifications(): NetworkResult<NotificationListDto> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getNotifications()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch notifications.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun markAllRead(): NetworkResult<Unit> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.markAllNotificationsRead()
            if (response.success) {
                NetworkResult.Success(Unit)
            } else {
                NetworkResult.Error(response.error?.message ?: "Failed to mark notifications read.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun markRead(notificationId: Int): NetworkResult<Unit> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.markNotificationRead(notificationId)
            if (response.success) {
                NetworkResult.Success(Unit)
            } else {
                NetworkResult.Error(response.error?.message ?: "Failed to mark notification read.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    private fun <T> handleException(error: Exception): NetworkResult<T> {
        return when (error) {
            is HttpException -> {
                val message = when (error.code()) {
                    401 -> "Sign in to view your notifications."
                    else -> "Notifications request failed (${error.code()})."
                }
                NetworkResult.Error(message, error.code().toString())
            }
            else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        }
    }
}
