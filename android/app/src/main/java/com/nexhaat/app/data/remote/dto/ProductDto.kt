package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProductDto(
    val id: Int,
    val name: String,
    val slug: String,
    val description: String? = null,
    @SerialName("brand_name")
    val brandName: String? = null,
    @SerialName("localized_name")
    val localizedName: String? = null,
    @SerialName("localized_description")
    val localizedDescription: String? = null,
    @SerialName("source_language")
    val sourceLanguage: String? = null,
    val price: String? = null,
    @SerialName("discount_price")
    val discountPrice: String? = null,
    @SerialName("display_price")
    val displayPrice: String? = null,
    val stock: Int? = null,
    val sku: String? = null,
    val variants: List<VariantDto> = emptyList(),
    val image: String? = null,
    @SerialName("display_image")
    val displayImage: String? = null,
    @SerialName("is_available")
    val isAvailable: Boolean = false,
    @SerialName("is_featured")
    val isFeatured: Boolean = false,
    @SerialName("moderation_status")
    val moderationStatus: String? = null,
    @SerialName("category_id")
    val categoryId: Int? = null,
    @SerialName("seller_id")
    val sellerId: Int? = null,
    @SerialName("created_at")
    val createdAt: String? = null,
    @SerialName("updated_at")
    val updatedAt: String? = null
) {
    /** The reference the website renders: the seller photo, else category artwork. */
    val imageReference: String?
        get() = displayImage?.takeIf(String::isNotBlank) ?: image?.takeIf(String::isNotBlank)
}

@Serializable
data class VariantDto(
    val id: Int,
    val sku: String? = null,
    @SerialName("option_name")
    val optionName: String? = null,
    @SerialName("option_value")
    val optionValue: String? = null,
    val price: String? = null,
    val stock: Int? = null
)
