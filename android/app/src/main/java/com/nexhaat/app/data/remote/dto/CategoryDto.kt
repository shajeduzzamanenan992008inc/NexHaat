package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CategoryDto(
    val id: Int,
    val name: String,
    val slug: String,
    val description: String? = null,
    val image: String? = null,
    @SerialName("is_active")
    val isActive: Boolean = true
)
