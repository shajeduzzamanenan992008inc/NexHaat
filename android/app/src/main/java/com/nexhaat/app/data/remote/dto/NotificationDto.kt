package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class NotificationListDto(
    val unread: Int = 0,
    val notifications: List<NotificationItemDto> = emptyList()
)

@Serializable
data class NotificationItemDto(
    val id: Int,
    val type: String = "general",
    val message: String,
    val link: String? = null,
    @SerialName("is_read")
    val isRead: Boolean = false,
    @SerialName("created_at")
    val createdAt: String? = null
)
