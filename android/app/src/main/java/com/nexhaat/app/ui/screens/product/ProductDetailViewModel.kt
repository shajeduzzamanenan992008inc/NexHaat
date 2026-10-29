package com.nexhaat.app.ui.screens.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CartRepository
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProductDetailUiState(
    val product: ProductDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val selectedVariantId: Int? = null,
    val isAddingToCart: Boolean = false,
    val cartMessage: String? = null,
    val requiresSignIn: Boolean = false
)

@HiltViewModel
class ProductDetailViewModel @Inject constructor(
    private val repository: CatalogRepository,
    private val cartRepository: CartRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProductDetailUiState())
    val uiState: StateFlow<ProductDetailUiState> = _uiState.asStateFlow()

    fun loadProduct(productId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getProductDetail(productId)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        product = result.data,
                        isLoading = false,
                        selectedVariantId = null
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        error = result.message,
                        isLoading = false
                    )
                }
                NetworkResult.Loading -> {}
            }
        }
    }

    fun selectVariant(variantId: Int) {
        _uiState.value = _uiState.value.copy(selectedVariantId = variantId, cartMessage = null)
    }

    fun addToCart() {
        val state = _uiState.value
        val product = state.product ?: return
        if (state.isAddingToCart) return
        val variants = product.variants
        if (variants.isNotEmpty() && state.selectedVariantId == null) {
            _uiState.value = state.copy(cartMessage = "Choose an option first.")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isAddingToCart = true, cartMessage = null, requiresSignIn = false)
            when (val result = cartRepository.add(product.id, state.selectedVariantId, 1)) {
                is NetworkResult.Success -> _uiState.value = _uiState.value.copy(
                    isAddingToCart = false,
                    cartMessage = "Added to your cart."
                )
                is NetworkResult.Error -> _uiState.value = _uiState.value.copy(
                    isAddingToCart = false,
                    cartMessage = result.message,
                    requiresSignIn = result.code == "401"
                )
                NetworkResult.Loading -> _uiState.value = _uiState.value.copy(isAddingToCart = false)
            }
        }
    }
}
