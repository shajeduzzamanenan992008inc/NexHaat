package com.nexhaat.app.data.remote

import org.junit.Assert.assertEquals
import org.junit.Test

class MediaBaseUrlResolverTest {
    private val placeholderFallback = "https://RELEASE_BASE_URL_REPLACE_ME/media/"
    private val debugBase = "http://10.0.2.2:5000/"
    private val releaseBase = "https://media.example.test/"

    @Test
    fun usesBuildTimeMediaBaseWhenMarkedResolved() {
        assertEquals(
            releaseBase,
            MediaBaseUrlResolver.resolvedOrFallbackString("true", releaseBase, placeholderFallback)
        )
    }

    @Test
    fun usesRuntimeFallbackWhenNotResolved() {
        assertEquals(
            placeholderFallback,
            MediaBaseUrlResolver.resolvedOrFallbackString("false", "", placeholderFallback)
        )
    }

    @Test
    fun resolvedDebugBaseResolvesAgainstTheLocalApiHost() {
        val mediaBase = MediaBaseUrlResolver.resolvedOrFallbackString(
            "true",
            debugBase,
            placeholderFallback
        )

        assertEquals(
            "http://10.0.2.2:5000/media/item.jpg",
            ImageUrlResolver.resolve("media/item.jpg", mediaBase)
        )
    }

    @Test
    fun unresolvedReleaseBaseNeverFabricatesAMediaHost() {
        val mediaBase = MediaBaseUrlResolver.resolvedOrFallbackString(
            "false",
            "",
            placeholderFallback
        )

        assertEquals(null, ImageUrlResolver.resolve("media/item.jpg", mediaBase))
    }
}
