package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class WishlistResponseDto(
    val count: Int = 0,
    val products: List<ProductDto> = emptyList()
)

@Serializable
data class AddWishlistRequest(
    @SerialName("product_id")
    val productId: Int
)

@Serializable
data class WishlistActionDto(
    @SerialName("product_id")
    val productId: Int,
    val saved: Boolean? = null,
    val removed: Boolean? = null
)
