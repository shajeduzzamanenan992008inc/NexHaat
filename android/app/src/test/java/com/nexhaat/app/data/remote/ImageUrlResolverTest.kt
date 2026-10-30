package com.nexhaat.app.data.remote

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ImageUrlResolverTest {
    private val mediaBaseUrl = "https://media.example.test/"

    @Test
    fun preservesValidAbsoluteHttpsUrl() {
        val imageUrl = "https://cdn.example.test/catalog/item.jpg"

        assertEquals(imageUrl, ImageUrlResolver.resolve(imageUrl, mediaBaseUrl))
    }

    @Test
    fun resolvesAbsoluteApiImageUrlsIndependentlyOfApiHost() {
        assertEquals(
            "https://cdn.example.test/catalog/item.jpg",
            ImageUrlResolver.resolve(
                "https://cdn.example.test/catalog/item.jpg",
                "http://10.0.2.2:5000/"
            )
        )
    }

    @Test
    fun keepsAbsoluteCdnUrlsWithEncodedKeysAndQueryStrings() {
        assertEquals(
            "https://cdn.example.test/products/a7f3c1.webp?v=2",
            ImageUrlResolver.resolve(
                "https://cdn.example.test/products/a7f3c1.webp?v=2",
                "https://cdn-other.example.test/"
            )
        )
    }

    @Test
    fun resolvesRelativePathAgainstMediaBaseUrl() {
        assertEquals(
            "https://media.example.test/catalog/item.jpg",
            ImageUrlResolver.resolve("catalog/item.jpg", mediaBaseUrl)
        )
    }

    @Test
    fun acceptsMediaBaseUrlWithoutTrailingSlash() {
        assertEquals(
            "https://media.example.test/cdn/products/item.webp",
            ImageUrlResolver.resolve(
                "products/item.webp",
                "https://media.example.test/cdn"
            )
        )
    }

    @Test
    fun resolvesRootRelativePathAgainstMediaHost() {
        assertEquals(
            "https://media.example.test/catalog/item.jpg",
            ImageUrlResolver.resolve("/catalog/item.jpg", mediaBaseUrl)
        )
    }

    @Test
    fun acceptsHttpForDevelopmentMediaHosts() {
        assertEquals(
            "http://10.0.2.2:5000/media/item.jpg",
            ImageUrlResolver.resolve("media/item.jpg", "http://10.0.2.2:5000/")
        )
    }

    @Test
    fun returnsNullForMissingOrBlankImage() {
        assertNull(ImageUrlResolver.resolve(null, mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("  ", mediaBaseUrl))
    }

    @Test
    fun rejectsUnsupportedSchemesAndProtocolRelativeUrls() {
        assertNull(ImageUrlResolver.resolve("file:///data/item.jpg", mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("//cdn.example.test/item.jpg", mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("javascript:alert(1)", mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("data:image/png;base64,AAAA", mediaBaseUrl))
    }

    @Test
    fun rejectsMalformedImageAndMediaBaseUrls() {
        assertNull(ImageUrlResolver.resolve("https://[invalid", mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("media/item.jpg", "not a URL"))
        assertNull(ImageUrlResolver.resolve("media/item.jpg", "file:///tmp/"))
        assertNull(ImageUrlResolver.resolve("catalog/item.jpg", ""))
    }

    @Test
    fun rejectsRelativeImagePathsThatEscapeTheMediaBase() {
        assertNull(ImageUrlResolver.resolve("../secrets/item.jpg", mediaBaseUrl))
        assertNull(ImageUrlResolver.resolve("catalog/../../item.jpg", mediaBaseUrl))
    }

    @Test
    fun rejectsBaseUrlsCarryingCredentialsOrQueries() {
        assertNull(ImageUrlResolver.resolve("item.jpg", "https://user:pass@media.example.test/"))
        assertNull(ImageUrlResolver.resolve("item.jpg", "https://media.example.test/?token=1"))
    }

    @Test
    fun rejectsRelativePathWhenMediaBaseIsBlank() {
        assertNull(ImageUrlResolver.resolve("catalog/item.jpg", ""))
        assertNull(ImageUrlResolver.resolve("catalog/item.jpg", "   "))
    }

    @Test
    fun rejectsRelativePathWhenMediaBaseIsPlaceholder() {
        assertNull(ImageUrlResolver.resolve("catalog/item.jpg", "https://RELEASE_BASE_URL_REPLACE_ME/"))
        assertNull(ImageUrlResolver.resolve("catalog/item.jpg", "https://replace_me_media.example/"))
    }

    @Test
    fun preservesAbsoluteUrlWhenMediaBaseIsUnresolved() {
        assertEquals(
            "https://cdn.example.test/item.jpg",
            ImageUrlResolver.resolve("https://cdn.example.test/item.jpg", "")
        )
        assertEquals(
            "https://cdn.example.test/item.jpg",
            ImageUrlResolver.resolve("https://cdn.example.test/item.jpg", "https://RELEASE_BASE_URL_REPLACE_ME/")
        )
    }

    @Test
    fun preservesValidAbsoluteHttpsUrlWithoutMediaBase() {
        val imageUrl = "https://cdn.example.test/catalog/item.jpg"

        assertEquals(imageUrl, ImageUrlResolver.resolveFromBackendAbsolute(imageUrl))
    }

    @Test
    fun absoluteBackendUrlIsIndependentOfMediaBaseInAbsoluteOnlyMode() {
        assertEquals(
            "https://cdn.example.test/catalog/item.jpg",
            ImageUrlResolver.resolveFromBackendAbsolute("https://cdn.example.test/catalog/item.jpg")
        )
    }

    @Test
    fun rejectsRelativePathsInAbsoluteOnlyMode() {
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("catalog/item.jpg"))
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("../secrets/item.jpg"))
    }

    @Test
    fun rejectsNonHttpAbsoluteUrlsInAbsoluteOnlyMode() {
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("file:///data/item.jpg"))
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("data:image/png;base64,AAAA"))
    }

    @Test
    fun rejectsBlankOrMalformedUrlsInAbsoluteOnlyMode() {
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute(null))
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("  "))
        assertNull(ImageUrlResolver.resolveFromBackendAbsolute("https://[invalid"))
    }

    @Test
    fun skipsPlaceholderMediaBaseWhenBackendReturnsValidAbsoluteUrl() {
        val backendImage = "https://cdn.example.test/products/a7f3c1.webp?v=2"
        assertEquals(
            backendImage,
            ImageUrlResolver.resolve(backendImage, "https://RELEASE_BASE_URL_REPLACE_ME/")
        )
    }
}
