package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CartDto(
    val items: List<CartItemDto> = emptyList(),
    val subtotal: String = "0.00",
    @SerialName("delivery_fee")
    val deliveryFee: String = "0.00",
    val total: String = "0.00"
)

@Serializable
data class CartItemDto(
    val key: String,
    @SerialName("product_id")
    val productId: Int,
    @SerialName("variant_id")
    val variantId: Int? = null,
    @SerialName("variant_label")
    val variantLabel: String? = null,
    val sku: String? = null,
    val name: String,
    val price: String,
    val quantity: Int,
    @SerialName("available_stock")
    val availableStock: Int,
    val subtotal: String
)

@Serializable
data class AddCartItemRequest(
    @SerialName("product_id")
    val productId: Int,
    @SerialName("variant_id")
    val variantId: Int? = null,
    val quantity: Int = 1
)

@Serializable
data class UpdateCartItemRequest(val quantity: Int)
