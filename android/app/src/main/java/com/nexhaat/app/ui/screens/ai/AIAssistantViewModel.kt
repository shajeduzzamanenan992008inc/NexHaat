package com.nexhaat.app.ui.screens.ai

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.dto.AIChatHistoryItemDto
import com.nexhaat.app.data.remote.dto.AIChatRequestDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val isUser: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)

data class AIAssistantUiState(
    val messages: List<ChatMessage> = listOf(
        ChatMessage(
            text = "Hello! I am NexHaat AI, your personal shopping assistant. I can help you find fresh groceries, compare prices, find top deals, and discover local sellers in Bangladesh. How can I help you today?",
            isUser = false
        )
    ),
    val inputText: String = "",
    val isGenerating: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class AIAssistantViewModel @Inject constructor(
    private val apiService: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(AIAssistantUiState())
    val uiState: StateFlow<AIAssistantUiState> = _uiState.asStateFlow()

    fun setInputText(value: String) {
        _uiState.value = _uiState.value.copy(inputText = value)
    }

    fun sendMessage(prompt: String = _uiState.value.inputText) {
        val cleanPrompt = prompt.trim()
        if (cleanPrompt.isBlank() || _uiState.value.isGenerating) return

        val userMessage = ChatMessage(text = cleanPrompt, isUser = true)
        val updatedMessages = _uiState.value.messages + userMessage
        _uiState.value = _uiState.value.copy(
            messages = updatedMessages,
            inputText = "",
            isGenerating = true,
            error = null
        )

        val historyPayload = updatedMessages.dropLast(1).map {
            AIChatHistoryItemDto(
                sender = if (it.isUser) "user" else "assistant",
                text = it.text
            )
        }

        viewModelScope.launch {
            try {
                val response = apiService.chatWithAI(
                    AIChatRequestDto(
                        message = cleanPrompt,
                        history = historyPayload
                    )
                )

                val aiText = response.responseText.trim()
                if (aiText.isNotEmpty()) {
                    _uiState.value = _uiState.value.copy(
                        messages = _uiState.value.messages + ChatMessage(text = aiText, isUser = false),
                        isGenerating = false
                    )
                } else {
                    val errorMsg = "NexHaat AI did not return a response. Please try again."
                    _uiState.value = _uiState.value.copy(
                        isGenerating = false,
                        error = errorMsg
                    )
                }
            } catch (e: Exception) {
                val fallbackMsg = "Could not reach AI service. Please check your internet connection."
                _uiState.value = _uiState.value.copy(
                    isGenerating = false,
                    error = fallbackMsg
                )
            }
        }
    }

    fun clearChat() {
        _uiState.value = AIAssistantUiState()
    }
}
