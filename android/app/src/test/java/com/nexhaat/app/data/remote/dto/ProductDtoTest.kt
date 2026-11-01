package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ProductDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun mapsBackendDisplayImageIntoTheRenderedReference() {
        val payload = """
            {
              "id": 7,
              "name": "Golden Kiwi",
              "slug": "golden-kiwi",
              "image": null,
              "display_image": "https://images.example.test/kiwi.jpg",
              "is_available": true
            }
        """.trimIndent()

        val product = json.decodeFromString<ProductDto>(payload)

        assertNull(product.image)
        assertEquals("https://images.example.test/kiwi.jpg", product.displayImage)
        assertEquals("https://images.example.test/kiwi.jpg", product.imageReference)
    }

    @Test
    fun fallsBackToTheSellerImageWhenDisplayImageIsMissing() {
        val payload = """
            {
              "id": 8,
              "name": "Honey",
              "slug": "honey",
              "image": "https://cdn.example.test/honey.webp",
              "is_available": true
            }
        """.trimIndent()

        val product = json.decodeFromString<ProductDto>(payload)

        assertEquals("https://cdn.example.test/honey.webp", product.imageReference)
    }

    @Test
    fun returnsNoReferenceWhenBothImageFieldsAreBlank() {
        val payload = """
            {
              "id": 9,
              "name": "Unknown",
              "slug": "unknown",
              "image": "",
              "display_image": "   ",
              "is_available": false
            }
        """.trimIndent()

        val product = json.decodeFromString<ProductDto>(payload)

        assertNull(product.imageReference)
    }
}
