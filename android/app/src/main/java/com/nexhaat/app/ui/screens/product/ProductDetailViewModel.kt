package com.nexhaat.app.ui.screens.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CartRepository
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
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
    val requiresSignIn: Boolean = false,
    val hasUnexpectedResult: Boolean = false
)

internal fun ProductDetailUiState.withProductResult(
    result: NetworkResult<ProductDto>
): ProductDetailUiState = when (result) {
    is NetworkResult.Success -> copy(
        product = result.data,
        isLoading = false,
        error = null,
        selectedVariantId = null,
        hasUnexpectedResult = false
    )
    is NetworkResult.Error -> copy(
        isLoading = false,
        error = result.message,
        hasUnexpectedResult = false
    )
    NetworkResult.Loading -> copy(
        isLoading = false,
        error = null,
        hasUnexpectedResult = true
    )
}

@HiltViewModel
class ProductDetailViewModel @Inject constructor(
    private val repository: CatalogRepository,
    private val cartRepository: CartRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProductDetailUiState())
    val uiState: StateFlow<ProductDetailUiState> = _uiState.asStateFlow()
    private var productJob: Job? = null
    private var requestedProductId: Int? = null

    fun loadProduct(productId: Int) {
        if (productJob?.isActive == true) {
            if (requestedProductId == productId) return
            productJob?.cancel()
        }
        requestedProductId = productId
        _uiState.value = _uiState.value.copy(
            product = null,
            isLoading = true,
            error = null,
            selectedVariantId = null,
            cartMessage = null,
            requiresSignIn = false,
            hasUnexpectedResult = false
        )
        productJob = viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.withProductResult(repository.getProductDetail(productId))
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = null,
                    hasUnexpectedResult = true
                )
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
