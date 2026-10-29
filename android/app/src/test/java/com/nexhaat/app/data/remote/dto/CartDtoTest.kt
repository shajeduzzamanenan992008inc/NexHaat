package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CartDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun deserializesServerCartWithVariantAndTotals() {
        val payload = """
            {
              "items": [
                {
                  "key": "12:4",
                  "product_id": 12,
                  "variant_id": 4,
                  "variant_label": "Size: Large",
                  "sku": "NH-12-L",
                  "name": "Cotton Panjabi",
                  "price": "1250.00",
                  "quantity": 2,
                  "available_stock": 5,
                  "subtotal": "2500.00"
                }
              ],
              "subtotal": "2500.00",
              "delivery_fee": "2.50",
              "total": "2502.50"
            }
        """.trimIndent()

        val cart = json.decodeFromString<CartDto>(payload)
        val item = cart.items.single()

        assertEquals("12:4", item.key)
        assertEquals(4, item.variantId)
        assertEquals("Size: Large", item.variantLabel)
        assertEquals(2, item.quantity)
        assertEquals(5, item.availableStock)
        assertEquals("2502.50", cart.total)
        assertTrue(item.subtotal.toBigDecimal() > item.price.toBigDecimal())
    }

    @Test
    fun deserializesEmptyCartWithZeroTotals() {
        val cart = json.decodeFromString<CartDto>(
            """{"items":[],"subtotal":"0.00","delivery_fee":"0.00","total":"0.00"}"""
        )

        assertTrue(cart.items.isEmpty())
        assertEquals("0.00", cart.subtotal)
    }

    @Test
    fun serializesAddItemRequestWithApiFieldNames() {
        val encoded = json.encodeToString(
            AddCartItemRequest.serializer(),
            AddCartItemRequest(productId = 7, variantId = 2, quantity = 3)
        )

        assertEquals("""{"product_id":7,"variant_id":2,"quantity":3}""", encoded)
    }
}
