package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.LoginRequestDto
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.remote.interceptor.CsrfInterceptor
import com.nexhaat.app.data.session.SessionManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val apiService: ApiService,
    private val csrfInterceptor: CsrfInterceptor,
    private val sessionManager: SessionManager
) {
    private val sessionOperationMutex = Mutex()

    suspend fun login(email: String, password: String): NetworkResult<UserDto> = withContext(Dispatchers.IO) {
        sessionOperationMutex.withLock {
            try {
                if (!refreshCsrfToken()) {
                    return@withLock NetworkResult.Error("Could not start a secure session.")
                }
                val response = apiService.login(LoginRequestDto(email, password))
                val user = response.data?.takeIf { response.success }
                    ?: return@withLock NetworkResult.Error(response.error?.message ?: "Sign-in failed.")
                if (!refreshCsrfToken()) {
                    sessionManager.clearSession()
                    return@withLock NetworkResult.Error("Could not refresh the secure session.")
                }
                sessionManager.authenticate(user)
                NetworkResult.Success(user)
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                networkError(error)
            }
        }
    }

    suspend fun logout(): NetworkResult<Boolean> = withContext(Dispatchers.IO) {
        sessionOperationMutex.withLock {
            try {
                if (!ensureCsrfToken()) {
                    return@withLock NetworkResult.Error("Could not start a secure session.")
                }
                val response = apiService.logout()
                if (response.success) NetworkResult.Success(true)
                else NetworkResult.Error(response.error?.message ?: "Sign-out failed.")
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                if (error is HttpException && error.code() == 401) {
                    NetworkResult.Error("Your session expired. Sign in again.", "401")
                } else {
                    networkError(error)
                }
            } finally {
                sessionManager.clearSession()
            }
        }
    }

    suspend fun revalidateSession(expectedUserId: Int? = null): NetworkResult<UserDto> =
        withContext(Dispatchers.IO) {
            sessionOperationMutex.withLock {
                try {
                    val response = apiService.getCurrentUser()
                    val user = response.data?.takeIf { response.success }
                        ?: run {
                            sessionManager.clearSession()
                            return@withLock NetworkResult.Error(
                                response.error?.message ?: "Could not verify the current session."
                            )
                        }
                    if (expectedUserId != null && user.id != expectedUserId) {
                        sessionManager.clearSession()
                        return@withLock NetworkResult.Error(
                            "The active account changed. Sign in with your password.",
                            "SESSION_ACCOUNT_MISMATCH"
                        )
                    }
                    sessionManager.authenticate(user)
                    NetworkResult.Success(user)
                } catch (error: CancellationException) {
                    throw error
                } catch (error: Exception) {
                    if (error is HttpException && error.code() == 401) {
                        sessionManager.clearSession()
                        NetworkResult.Error("Your session expired. Sign in with your password.", "401")
                    } else {
                        networkError(error)
                    }
                }
            }
        }

    suspend fun ensureCsrfToken(): Boolean = withContext(Dispatchers.IO) {
        if (csrfInterceptor.hasCsrfToken()) return@withContext true
        refreshCsrfToken()
    }

    private suspend fun refreshCsrfToken(): Boolean {
        val response = apiService.getCsrfToken()
        val token = response.data?.csrfToken?.takeIf { response.success && it.isNotBlank() }
            ?: return false
        csrfInterceptor.setCsrfToken(token)
        return true
    }

    private fun <T> networkError(error: Exception): NetworkResult<T> = when (error) {
        is HttpException -> NetworkResult.Error(
            if (error.code() == 401) "Invalid email or password." else "Request failed (${error.code()}).",
            error.code().toString()
        )
        else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
    }

}
