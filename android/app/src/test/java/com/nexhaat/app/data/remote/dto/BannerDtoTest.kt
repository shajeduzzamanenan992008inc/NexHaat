package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class BannerDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun parsesMinimalActiveBanner() {
        val payload = """
            {
              "id": 1,
              "title": "Fresh arrivals",
              "image_url": "https://cdn.example.test/banner.webp"
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertEquals(1, banner.id)
        assertEquals("Fresh arrivals", banner.title)
        assertNull(banner.subtitle)
        assertEquals("https://cdn.example.test/banner.webp", banner.imageUrl)
        assertEquals("products", banner.linkType)
        assertTrue(banner.isActive)
        assertEquals(0, banner.displayOrder)
    }

    @Test
    fun parsesFullBannerWithLinkNavigation() {
        val payload = """
            {
              "id": 2,
              "title": "Seasonal offer",
              "subtitle": "Explore seasonal favorites",
              "image_url": "https://cdn.example.test/seasonal.webp",
              "link_url": "https://nexhaat.example.test/seasonal",
              "link_type": "category",
              "is_active": true,
              "display_order": 3
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertEquals(2, banner.id)
        assertEquals("Seasonal offer", banner.title)
        assertEquals("Explore seasonal favorites", banner.subtitle)
        assertEquals("https://cdn.example.test/seasonal.webp", banner.imageUrl)
        assertEquals("https://nexhaat.example.test/seasonal", banner.linkUrl)
        assertEquals("category", banner.linkType)
        assertTrue(banner.isActive)
        assertEquals(3, banner.displayOrder)
    }

    @Test
    fun parsesBannerWithProductsLinkType() {
        val payload = """
            {
              "id": 3,
              "title": "Best sellers",
              "image_url": "https://cdn.example.test/best.webp",
              "link_type": "products"
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertEquals("products", banner.linkType)
        assertNull(banner.linkUrl)
    }

    @Test
    fun normalizesLinkTypeToProductsWhenOmitted() {
        val payload = """
            {
              "id": 4,
              "title": "Hero banner",
              "image_url": "https://cdn.example.test/hero.webp"
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertEquals("products", banner.linkType)
    }

    @Test
    fun preservesInactiveAndZeroOrderBanner() {
        val payload = """
            {
              "id": 5,
              "title": "Expired campaign",
              "image_url": "https://cdn.example.test/old.webp",
              "link_type": "search",
              "is_active": false,
              "display_order": -1
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertFalse(banner.isActive)
        assertEquals("search", banner.linkType)
        assertEquals(-1, banner.displayOrder)
    }

    @Test
    fun acceptsBannerWithoutAnyImage() {
        val payload = """
            {
              "id": 6,
              "title": "Text-only banner",
              "subtitle": "Shop now",
              "link_type": "external",
              "link_url": "https://nexhaat.example.test/promo"
            }
        """.trimIndent()

        val banner = json.decodeFromString<BannerDto>(payload)

        assertNull(banner.imageUrl)
        assertEquals("Text-only banner", banner.title)
        assertEquals("Shop now", banner.subtitle)
        assertEquals("external", banner.linkType)
        assertEquals("https://nexhaat.example.test/promo", banner.linkUrl)
    }
}
