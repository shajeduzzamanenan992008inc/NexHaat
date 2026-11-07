package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ForgotPasswordRequestDto
import com.nexhaat.app.data.remote.dto.LoginRequestDto
import com.nexhaat.app.data.remote.dto.RegisterRequestDto
import com.nexhaat.app.data.remote.dto.RegistrationChallengeDto
import com.nexhaat.app.data.remote.dto.ResetPasswordRequestDto
import com.nexhaat.app.data.remote.dto.SocialLoginRequestDto
import com.nexhaat.app.data.remote.dto.TotpSetupDto
import com.nexhaat.app.data.remote.dto.TotpVerifyRequestDto
import com.nexhaat.app.data.remote.dto.TwoFactorChallengeRequestDto
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.remote.dto.VerifyRegistrationRequestDto
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
                if (response.twoFactorRequired) {
                    if (!refreshCsrfToken()) {
                        return@withLock NetworkResult.Error("Could not refresh the secure session.")
                    }
                    return@withLock NetworkResult.Error(response.message ?: "Two-factor authentication required.", "TWO_FACTOR_REQUIRED")
                }
                val user = response.data?.takeIf { response.success }
                    ?: return@withLock NetworkResult.Error(response.error?.message ?: response.message ?: "Sign-in failed.")
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

    suspend fun register(
        email: String,
        fullName: String,
        phone: String,
        password: String,
        role: String = "customer",
        storeName: String? = null
    ): NetworkResult<RegistrationChallengeDto> = withContext(Dispatchers.IO) {
        try {
            if (!refreshCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            val request = RegisterRequestDto(
                role = role,
                email = email,
                fullName = fullName,
                phone = phone,
                password = password,
                storeName = storeName
            )
            val response = apiService.register(request)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Registration failed.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            networkError(error)
        }
    }

    suspend fun verifyRegistration(code: String): NetworkResult<UserDto> = withContext(Dispatchers.IO) {
        sessionOperationMutex.withLock {
            try {
                if (!ensureCsrfToken()) {
                    return@withLock NetworkResult.Error("Could not start a secure session.")
                }
                val response = apiService.verifyRegistration(VerifyRegistrationRequestDto(code))
                val user = response.data?.takeIf { response.success }
                    ?: return@withLock NetworkResult.Error(response.error?.message ?: response.message ?: "Verification failed.")
                refreshCsrfToken()
                sessionManager.authenticate(user)
                NetworkResult.Success(user)
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                networkError(error)
            }
        }
    }

    suspend fun forgotPassword(email: String): NetworkResult<String> = withContext(Dispatchers.IO) {
        try {
            if (!ensureCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            val response = apiService.forgotPassword(ForgotPasswordRequestDto(email))
            if (response.success) {
                NetworkResult.Success(response.message ?: "Verification code sent to your email.")
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to process request.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            networkError(error)
        }
    }

    suspend fun resetPassword(email: String, code: String, newPass: String): NetworkResult<String> = withContext(Dispatchers.IO) {
        try {
            if (!ensureCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            val response = apiService.resetPassword(ResetPasswordRequestDto(email, code, newPass))
            if (response.success) {
                NetworkResult.Success(response.message ?: "Password reset successfully. Sign in with your new password.")
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Password reset failed.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            networkError(error)
        }
    }

    // Provider sign-in must prove identity with a token the server verifies. Email and
    // display name are never sent: the server must not trust client-supplied identity.
    suspend fun socialLogin(provider: String, idToken: String): NetworkResult<UserDto> = withContext(Dispatchers.IO) {
        sessionOperationMutex.withLock {
            try {
                if (!refreshCsrfToken()) {
                    return@withLock NetworkResult.Error("Could not start a secure session.")
                }
                val response = apiService.socialLogin(SocialLoginRequestDto(provider, idToken))
                val user = response.data?.takeIf { response.success }
                    ?: return@withLock NetworkResult.Error(response.error?.message ?: response.message ?: "Social sign-in failed.")
                refreshCsrfToken()
                sessionManager.authenticate(user)
                NetworkResult.Success(user)
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                networkError(error)
            }
        }
    }

    suspend fun setupTotp(): NetworkResult<TotpSetupDto> = withContext(Dispatchers.IO) {
        try {
            if (!ensureCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            val response = apiService.setupTotp()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Could not initiate 2FA setup.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            networkError(error)
        }
    }

    suspend fun verifyTotp(code: String): NetworkResult<String> = withContext(Dispatchers.IO) {
        try {
            if (!ensureCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            val response = apiService.verifyTotp(TotpVerifyRequestDto(code))
            if (response.success) {
                NetworkResult.Success(response.message ?: "Two-factor authentication enabled successfully.")
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Invalid 2FA code.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            networkError(error)
        }
    }

    suspend fun challengeTotp(code: String): NetworkResult<UserDto> = withContext(Dispatchers.IO) {
        sessionOperationMutex.withLock {
            try {
                if (!ensureCsrfToken()) {
                    return@withLock NetworkResult.Error("Could not start a secure session.")
                }
                val response = apiService.challengeTotp(TwoFactorChallengeRequestDto(code))
                val user = response.data?.takeIf { response.success }
                    ?: return@withLock NetworkResult.Error(response.error?.message ?: response.message ?: "2FA challenge verification failed.")
                refreshCsrfToken()
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
        return try {
            val response = apiService.getCsrfToken()
            val token = response.data?.csrfToken?.takeIf { response.success && it.isNotBlank() }
                ?: return false
            csrfInterceptor.setCsrfToken(token)
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun <T> networkError(error: Exception): NetworkResult<T> = when (error) {
        is HttpException -> NetworkResult.Error(
            if (error.code() == 401) "Invalid credentials or session expired." else "Request failed (${error.code()}).",
            error.code().toString()
        )
        else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
    }
}
