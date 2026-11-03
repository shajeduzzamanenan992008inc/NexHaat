package com.nexhaat.app.ui.screens.products

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
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
    val hasMore: Boolean = true,
    val hasUnexpectedResult: Boolean = false
)

internal fun ProductsUiState.withResult(
    result: NetworkResult<Pair<List<ProductDto>, com.nexhaat.app.data.remote.dto.Pagination?>>,
    page: Int,
    refresh: Boolean
): ProductsUiState = when (result) {
    is NetworkResult.Success -> copy(
        products = if (refresh) result.data.first else products + result.data.first,
        isLoading = false,
        error = null,
        currentPage = page + 1,
        hasMore = result.data.second?.let { page < (it.total + it.limit - 1) / it.limit } ?: false,
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
class ProductsViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProductsUiState())
    val uiState: StateFlow<ProductsUiState> = _uiState.asStateFlow()
    private var productsJob: Job? = null
    private var currentRequestKey: Pair<Int?, String?>? = null

    fun loadProducts(categoryId: Int? = null, query: String? = null, refresh: Boolean = false) {
        val requestKey = categoryId to query
        if (productsJob?.isActive == true) {
            if (!refresh) return
            productsJob?.cancel()
        }
        val requestKeyChanged = requestKey != currentRequestKey
        currentRequestKey = requestKey

        val page = if (refresh) 1 else _uiState.value.currentPage
        _uiState.value = _uiState.value.copy(
            products = if (refresh && requestKeyChanged) emptyList() else _uiState.value.products,
            isLoading = true,
            error = null,
            currentPage = if (refresh) 1 else _uiState.value.currentPage,
            hasUnexpectedResult = false
        )
        productsJob = viewModelScope.launch {
            try {
                val result = if (query != null) {
                    repository.searchProducts(query, page)
                } else {
                    repository.getProducts(page = page, categoryId = categoryId)
                }
                _uiState.value = _uiState.value.withResult(result, page, refresh)
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
    
    fun loadMore(categoryId: Int? = null, query: String? = null) {
        if (_uiState.value.hasMore && !_uiState.value.isLoading) {
            loadProducts(categoryId, query, refresh = false)
        }
    }
}
