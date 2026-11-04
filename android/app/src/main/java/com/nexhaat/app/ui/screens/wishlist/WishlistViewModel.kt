package com.nexhaat.app.ui.screens.wishlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CartRepository
import com.nexhaat.app.data.repository.WishlistRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface WishlistUiState {
    object Loading : WishlistUiState
    data class Success(val products: List<ProductDto>) : WishlistUiState
    data class Error(val message: String) : WishlistUiState
}

@HiltViewModel
class WishlistViewModel @Inject constructor(
    private val wishlistRepository: WishlistRepository,
    private val cartRepository: CartRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<WishlistUiState>(WishlistUiState.Loading)
    val uiState: StateFlow<WishlistUiState> = _uiState.asStateFlow()

    private val _actionMessage = MutableStateFlow<String?>(null)
    val actionMessage: StateFlow<String?> = _actionMessage.asStateFlow()

    init {
        loadWishlist()
    }

    fun loadWishlist() {
        viewModelScope.launch {
            _uiState.value = WishlistUiState.Loading
            when (val result = wishlistRepository.getWishlist()) {
                is NetworkResult.Success -> _uiState.value = WishlistUiState.Success(result.data)
                is NetworkResult.Error -> _uiState.value = WishlistUiState.Error(result.message)
                NetworkResult.Loading -> Unit
            }
        }
    }

    fun removeFromWishlist(productId: Int) {
        viewModelScope.launch {
            when (val result = wishlistRepository.remove(productId)) {
                is NetworkResult.Success -> {
                    _actionMessage.value = "Item removed from wishlist"
                    loadWishlist()
                }
                is NetworkResult.Error -> _actionMessage.value = result.message
                NetworkResult.Loading -> Unit
            }
        }
    }

    fun moveToCart(product: ProductDto) {
        viewModelScope.launch {
            when (val result = cartRepository.add(product.id, null, 1)) {
                is NetworkResult.Success -> {
                    wishlistRepository.remove(product.id)
                    _actionMessage.value = "${product.name} moved to cart"
                    loadWishlist()
                }
                is NetworkResult.Error -> _actionMessage.value = result.message
                NetworkResult.Loading -> Unit
            }
        }
    }

    fun dismissActionMessage() {
        _actionMessage.value = null
    }
}
