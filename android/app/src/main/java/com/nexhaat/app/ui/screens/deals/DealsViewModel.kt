package com.nexhaat.app.ui.screens.deals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.BannerDto
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CartRepository
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface DealsUiState {
    object Loading : DealsUiState
    data class Success(
        val deals: List<ProductDto>,
        val banners: List<BannerDto>
    ) : DealsUiState
    data class Error(val message: String) : DealsUiState
}

@HiltViewModel
class DealsViewModel @Inject constructor(
    private val catalogRepository: CatalogRepository,
    private val cartRepository: CartRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<DealsUiState>(DealsUiState.Loading)
    val uiState: StateFlow<DealsUiState> = _uiState.asStateFlow()

    private val _actionMessage = MutableStateFlow<String?>(null)
    val actionMessage: StateFlow<String?> = _actionMessage.asStateFlow()

    init {
        loadDeals()
    }

    fun loadDeals() {
        viewModelScope.launch {
            _uiState.value = DealsUiState.Loading
            val productsResult = catalogRepository.getProducts(limit = 50)
            val bannersResult = catalogRepository.getBanners(limit = 5)

            if (productsResult is NetworkResult.Success) {
                val allProducts = productsResult.data.first
                // Filter for products that have a discount or are featured as deals
                val discounted = allProducts.filter {
                    val hasDiscount = !it.discountPrice.isNullOrBlank() && it.discountPrice != it.price
                    hasDiscount || it.isFeatured
                }.ifEmpty { allProducts.take(10) }

                val banners = (bannersResult as? NetworkResult.Success)?.data ?: emptyList()
                _uiState.value = DealsUiState.Success(discounted, banners)
            } else if (productsResult is NetworkResult.Error) {
                _uiState.value = DealsUiState.Error(productsResult.message)
            }
        }
    }

    fun addToCart(product: ProductDto) {
        viewModelScope.launch {
            val result = cartRepository.add(product.id, null, 1)
            when (result) {
                is NetworkResult.Success -> _actionMessage.value = "${product.name} added to cart"
                is NetworkResult.Error -> _actionMessage.value = result.message
            }
        }
    }

    fun dismissActionMessage() {
        _actionMessage.value = null
    }
}
