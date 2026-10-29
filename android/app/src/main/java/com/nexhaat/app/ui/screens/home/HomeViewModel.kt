package com.nexhaat.app.ui.screens.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.remote.dto.ProductDto
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val categories: List<CategoryDto> = emptyList(),
    val products: List<ProductDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadHomeData()
    }

    fun loadHomeData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            val (categoriesResult, productsResult) = coroutineScope {
                val categoriesRequest = async { repository.getCategories() }
                val productsRequest = async { repository.getProducts(page = 1, limit = 10) }
                categoriesRequest.await() to productsRequest.await()
            }
            
            when {
                categoriesResult is NetworkResult.Success && productsResult is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        categories = categoriesResult.data,
                        products = productsResult.data.first,
                        isLoading = false
                    )
                }
                categoriesResult is NetworkResult.Error && productsResult is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        categories = emptyList(),
                        products = productsResult.data.first,
                        error = categoriesResult.message,
                        isLoading = false
                    )
                }
                productsResult is NetworkResult.Error && categoriesResult is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        categories = categoriesResult.data,
                        products = emptyList(),
                        error = productsResult.message,
                        isLoading = false
                    )
                }
                categoriesResult is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        categories = emptyList(),
                        products = emptyList(),
                        error = categoriesResult.message,
                        isLoading = false
                    )
                }
                productsResult is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        categories = emptyList(),
                        products = emptyList(),
                        error = productsResult.message,
                        isLoading = false
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }
            }
        }
    }
}
