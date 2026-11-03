package com.nexhaat.app.data.remote.interceptor

import okhttp3.Cookie
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.junit.Assert.assertEquals
import org.junit.Test

class PersistentCookieJarTest {

    @Test
    fun clearRemovesInMemorySessionCookies() {
        val url = "https://api.example.test/".toHttpUrl()
        val cookie = Cookie.Builder()
            .name("session")
            .value("test-session")
            .hostOnlyDomain(url.host)
            .build()
        val jar = PersistentCookieJar()
        jar.loadForRequest(url)
        jar.saveFromResponse(url, listOf(cookie))

        assertEquals(listOf(cookie), jar.loadForRequest(url))
        jar.clear()
        assertEquals(emptyList<Cookie>(), jar.loadForRequest(url))
    }

    @Test
    fun responseStartedBeforeClearCannotRestoreSessionCookie() {
        val url = "https://api.example.test/".toHttpUrl()
        val cookie = Cookie.Builder()
            .name("session")
            .value("test-session")
            .hostOnlyDomain(url.host)
            .build()
        val jar = PersistentCookieJar()
        jar.loadForRequest(url)

        jar.clear()
        jar.saveFromResponse(url, listOf(cookie))

        assertEquals(emptyList<Cookie>(), jar.loadForRequest(url))
    }
}
