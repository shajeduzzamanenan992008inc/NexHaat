package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Remote banner card from the backend home banner endpoint.
 *
 * Used by [NexHaatBannerCarousel] and fed from [com.nexhaat.app.data.repository.CatalogRepository]
 * through [com.nexhaat.app.ui.screens.home.HomeViewModel].
 */
@Serializable
data class BannerDto(
    val id: Int,
    val title: String,
    val subtitle: String? = null,
    @SerialName("image_url")
    val imageUrl: String? = null,
    @SerialName("link_url")
    val linkUrl: String? = null,
    @SerialName("link_type")
    val linkType: String = "products",
    @SerialName("is_active")
    val isActive: Boolean = true,
    @SerialName("display_order")
    val displayOrder: Int = 0
)
