package com.nexhaat.app.data.remote.interceptor

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException
import java.lang.reflect.Proxy

class SafeNetworkLoggingInterceptorTest {

    @Test
    fun logsOnlyNonSensitiveRequestMetadata() {
        val request = Request.Builder()
            .url(
                "https://userinfo-marker@api.example.test/api/v1/auth/login" +
                    "?value=query-marker"
            )
            .header("Cookie", "cookie-marker")
            .header("Authorization", "authorization-marker")
            .header("X-CSRFToken", "csrf-marker")
            .post(
                """{"value":"body-marker"}"""
                    .toRequestBody("application/json".toMediaType())
            )
            .build()
        val response = Response.Builder()
            .request(request)
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .build()
        val logs = mutableListOf<String>()
        val chain = Proxy.newProxyInstance(
            Interceptor.Chain::class.java.classLoader,
            arrayOf(Interceptor.Chain::class.java)
        ) { _, method, _ ->
            when (method.name) {
                "request" -> request
                "proceed" -> response
                else -> throw IOException("Unexpected chain method")
            }
        } as Interceptor.Chain

        SafeNetworkLoggingInterceptor(logs::add).intercept(chain)

        val output = logs.joinToString("\n")
        assertTrue(output.contains("POST https://api.example.test"))
        listOf(
            "userinfo-marker",
            "query-marker",
            "cookie-marker",
            "authorization-marker",
            "csrf-marker",
            "body-marker",
            "/api/v1/auth/login"
        ).forEach { sensitiveValue ->
            assertFalse("Log exposed $sensitiveValue", output.contains(sensitiveValue))
        }
    }
}
