package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.LoginRequestDto
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.remote.interceptor.CsrfInterceptor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val apiService: ApiService,
    private val csrfInterceptor: CsrfInterceptor
) {
    suspend fun login(email: String, password: String): NetworkResult<UserDto> = withContext(Dispatchers.IO) {
        try {
            refreshCsrfToken() ?: return@withContext NetworkResult.Error("Could not start a secure session.")
            val response = apiService.login(LoginRequestDto(email, password))
            val user = response.data?.takeIf { response.success }
                ?: return@withContext NetworkResult.Error(response.error?.message ?: "Sign-in failed.")
            // The session changes on login, so the write token must be refreshed before cart calls.
            refreshCsrfToken() ?: return@withContext NetworkResult.Error("Could not refresh the secure session.")
            NetworkResult.Success(user)
        } catch (error: Exception) {
            networkError(error)
        }
    }

    suspend fun logout(): NetworkResult<Boolean> = withContext(Dispatchers.IO) {
        try {
            ensureCsrfToken() ?: return@withContext NetworkResult.Error("Could not start a secure session.")
            val response = apiService.logout()
            csrfInterceptor.clearCsrfToken()
            if (response.success) NetworkResult.Success(true)
            else NetworkResult.Error(response.error?.message ?: "Sign-out failed.")
        } catch (error: Exception) {
            csrfInterceptor.clearCsrfToken()
            networkError(error)
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
