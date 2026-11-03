package com.nexhaat.app.data.remote.interceptor

import android.util.Log
import okhttp3.HttpUrl
import okhttp3.Interceptor
import okhttp3.Response
import java.util.concurrent.TimeUnit

/**
 * Logs only the method, host, status, and duration. Paths, query strings, headers,
 * bodies, and exception messages may contain private data and are intentionally omitted.
 */
class SafeNetworkLoggingInterceptor(
    private val log: (String) -> Unit = { Log.d(TAG, it) }
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val label = safeRequestLabel(request.method, request.url)
        val startedAt = System.nanoTime()
        log("--> $label")
        return try {
            val response = chain.proceed(request)
            val elapsedMillis = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startedAt)
            log("<-- ${response.code} $label (${elapsedMillis}ms)")
            response
        } catch (error: Exception) {
            log("<-- FAILED $label (${error.javaClass.simpleName})")
            throw error
        }
    }

    internal companion object {
        private const val TAG = "NexHaatNetwork"

        fun safeRequestLabel(method: String, url: HttpUrl): String =
            "$method ${url.scheme}://${url.host}"
    }
}
