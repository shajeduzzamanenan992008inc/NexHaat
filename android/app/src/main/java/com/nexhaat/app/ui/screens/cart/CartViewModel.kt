package com.nexhaat.app.ui.screens.cart

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.repository.CartRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CartUiState(
    val cart: CartDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class CartViewModel @Inject constructor(
    private val repository: CartRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(CartUiState())
    val uiState: StateFlow<CartUiState> = _uiState.asStateFlow()

    fun loadCart() = runCartRequest { repository.getCart() }

    fun updateQuantity(key: String, quantity: Int) =
        runCartRequest { repository.update(key, quantity) }

    fun remove(key: String) = runCartRequest { repository.remove(key) }

    fun add(productId: Int, variantId: Int?, quantity: Int = 1) =
        runCartRequest { repository.add(productId, variantId, quantity) }

    private fun runCartRequest(action: suspend () -> NetworkResult<CartDto>) {
        if (_uiState.value.isLoading) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = action()) {
                is NetworkResult.Success -> _uiState.value = CartUiState(cart = result.data)
                is NetworkResult.Error -> _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = result.message
                )
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }
}
