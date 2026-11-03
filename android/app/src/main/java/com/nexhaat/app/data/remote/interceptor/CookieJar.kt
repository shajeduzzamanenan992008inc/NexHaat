package com.nexhaat.app.data.remote.interceptor

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

/** Keeps the Flask session cookie for the lifetime of this app process. */
class PersistentCookieJar : CookieJar {
    private val cookieStore = mutableListOf<Cookie>()
    private val requestGeneration = ThreadLocal<Long>()
    private var generation = 0L

    @Synchronized
    fun clear() {
        generation += 1
        cookieStore.clear()
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val requestGeneration = this.requestGeneration.get()
        this.requestGeneration.remove()
        if (requestGeneration != null && requestGeneration != generation) return

        val now = System.currentTimeMillis()
        cookieStore.removeAll { it.expiresAt <= now }
        cookies.forEach { incoming ->
            cookieStore.removeAll { existing ->
                existing.name == incoming.name &&
                    existing.domain == incoming.domain &&
                    existing.path == incoming.path
            }
            if (incoming.expiresAt > now) cookieStore += incoming
        }
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        requestGeneration.set(generation)
        val now = System.currentTimeMillis()
        cookieStore.removeAll { it.expiresAt <= now }
        return cookieStore.filter { it.matches(url) }
    }
}
