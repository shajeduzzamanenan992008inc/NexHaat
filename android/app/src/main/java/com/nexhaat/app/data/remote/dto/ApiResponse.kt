package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ApiResponse<T>(
    val success: Boolean = false,
    val data: T? = null,
    val message: String? = null,
    val pagination: Pagination? = null,
    val error: ApiError? = null,
    @SerialName("two_factor_required")
    val twoFactorRequired: Boolean = false
)

@Serializable
data class Pagination(
    val page: Int = 1,
    val limit: Int = 20,
    val total: Int = 0
)

@Serializable
data class ApiError(
    val code: String? = null,
    val message: String? = null
)
