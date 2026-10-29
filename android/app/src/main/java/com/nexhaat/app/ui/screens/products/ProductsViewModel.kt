package com.nexhaat.app.ui.screens.products

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProductsUiState(
    val products: List<ProductDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val currentPage: Int = 1,
    val hasMore: Boolean = true
)

@HiltViewModel
class ProductsViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProductsUiState())
    val uiState: StateFlow<ProductsUiState> = _uiState.asStateFlow()

    fun loadProducts(categoryId: Int? = null, query: String? = null, refresh: Boolean = false) {
        viewModelScope.launch {
            if (refresh) {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null, currentPage = 1)
            } else {
                if (_uiState.value.isLoading) return@launch
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            }
            
            val page = if (refresh) 1 else _uiState.value.currentPage
            val result = if (query != null) {
                repository.searchProducts(query, page)
            } else {
                repository.getProducts(page = page, categoryId = categoryId)
            }
            
            when (result) {
                is NetworkResult.Success -> {
                    val newProducts = if (refresh) result.data.first else _uiState.value.products + result.data.first
                    _uiState.value = _uiState.value.copy(
                        products = newProducts,
                        isLoading = false,
                        currentPage = page + 1,
                        hasMore = result.data.second?.let { page < (it.total + it.limit - 1) / it.limit } ?: false
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
    
    fun loadMore(categoryId: Int? = null, query: String? = null) {
        if (_uiState.value.hasMore && !_uiState.value.isLoading) {
            loadProducts(categoryId, query, refresh = false)
        }
    }
}
