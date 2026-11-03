package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AIChatRequestDto(
    val message: String,
    val prompt: String = message,
    val history: List<AIChatHistoryItemDto> = emptyList(),
    val messages: List<AIChatHistoryItemDto> = history,
    val model: String = "gemini-3.8-flash",
    val role: String = "shopping"
)

@Serializable
data class AIChatHistoryItemDto(
    val sender: String,
    val text: String
)

@Serializable
data class AIChatResponseDto(
    val reply: String? = null,
    val text: String? = null,
    @SerialName("suggested_products")
    val suggestedProducts: List<Int> = emptyList()
) {
    val responseText: String
        get() = reply ?: text ?: ""
}
