package com.nexhaat.app.data.remote.interceptor

import com.nexhaat.app.data.session.SessionManager
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionExpiryInterceptor @Inject constructor(
    private val sessionManager: SessionManager
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val response = chain.proceed(request)
        if (response.code == 401 && request.url.encodedPath != LOGIN_PATH) {
            sessionManager.clearSession()
        }
        return response
    }

    private companion object {
        const val LOGIN_PATH = "/api/v1/auth/login"
    }
}
