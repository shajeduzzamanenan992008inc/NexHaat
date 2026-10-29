package com.nexhaat.app.data.remote.interceptor

import okhttp3.Interceptor
import okhttp3.Response

class CsrfInterceptor : Interceptor {
    @Volatile
    private var csrfToken: String? = null

    fun setCsrfToken(token: String) {
        csrfToken = token
    }

    fun hasCsrfToken(): Boolean = !csrfToken.isNullOrBlank()

    fun clearCsrfToken() {
        csrfToken = null
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val method = originalRequest.method
        
        if (method == "POST" || method == "PUT" || method == "PATCH" || method == "DELETE") {
            val token = csrfToken
            if (token != null) {
                val request = originalRequest.newBuilder()
                    .header("X-CSRFToken", token)
                    .build()
                return chain.proceed(request)
            }
        }
        return chain.proceed(originalRequest)
    }
}
