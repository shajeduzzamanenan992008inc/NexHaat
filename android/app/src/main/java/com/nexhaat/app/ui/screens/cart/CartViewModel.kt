package com.nexhaat.app.ui.screens.cart

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.repository.CartRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CartUiState(
    val cart: CartDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val errorCode: String? = null,
    val hasUnexpectedResult: Boolean = false
)

internal fun CartUiState.withResult(result: NetworkResult<CartDto>): CartUiState = when (result) {
    is NetworkResult.Success -> CartUiState(cart = result.data)
    is NetworkResult.Error -> copy(
        isLoading = false,
        error = result.message,
        errorCode = result.code,
        hasUnexpectedResult = false
    )
    NetworkResult.Loading -> copy(
        isLoading = false,
        error = null,
        errorCode = null,
        hasUnexpectedResult = true
    )
}

@HiltViewModel
class CartViewModel @Inject constructor(
    private val repository: CartRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(CartUiState())
    val uiState: StateFlow<CartUiState> = _uiState.asStateFlow()
    private var cartJob: Job? = null

    fun loadCart() = runCartRequest { repository.getCart() }

    fun updateQuantity(key: String, quantity: Int) =
        runCartRequest { repository.update(key, quantity) }

    fun remove(key: String) = runCartRequest { repository.remove(key) }

    fun add(productId: Int, variantId: Int?, quantity: Int = 1) =
        runCartRequest { repository.add(productId, variantId, quantity) }

    private fun runCartRequest(action: suspend () -> NetworkResult<CartDto>) {
        if (cartJob?.isActive == true) return
        cartJob = viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                errorCode = null,
                hasUnexpectedResult = false
            )
            try {
                _uiState.value = _uiState.value.withResult(action())
            } catch (error: CancellationException) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = null,
                    errorCode = null,
                    hasUnexpectedResult = false
                )
                throw error
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = null,
                    errorCode = null,
                    hasUnexpectedResult = true
                )
            } finally {
                if (_uiState.value.isLoading) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = null,
                        errorCode = null,
                        hasUnexpectedResult = true
                    )
                }
            }
        }
    }
}
