package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class CsrfTokenDto(
    @SerialName("csrf_token")
    val csrfToken: String
)

@Serializable
data class LoginRequestDto(
    val email: String,
    val password: String
)

@Serializable
data class UserDto(
    val id: Int,
    val email: String,
    val role: String,
    @SerialName("is_active")
    val isActive: Boolean = true,
    @SerialName("preferred_locale")
    val preferredLocale: String? = null
)

@Serializable
data class ApiMessageDto(
    val message: String? = null,
    val data: JsonElement? = null
)
