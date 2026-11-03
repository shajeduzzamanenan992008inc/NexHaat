package com.nexhaat.app.ui.screens.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.BannerDto
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.remote.dto.ProductDto
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val categories: List<CategoryDto> = emptyList(),
    val products: List<ProductDto> = emptyList(),
    val banners: List<BannerDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()
    private var homeJob: Job? = null

    init {
        loadHomeData()
    }

    fun loadHomeData() {
        if (homeJob?.isActive == true) return
        homeJob = viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            val categoriesResult = async { repository.getCategories() }
            val productsResult = async { repository.getProducts(page = 1, limit = 20) }
            val bannersResult = async { repository.getBanners() }

            val categories = (categoriesResult.await() as? NetworkResult.Success)?.data.orEmpty()
            val products = (productsResult.await() as? NetworkResult.Success)?.data?.first.orEmpty()
            val banners = (bannersResult.await() as? NetworkResult.Success)?.data.orEmpty()
            val error = (productsResult.await() as? NetworkResult.Error)?.message
                ?: (categoriesResult.await() as? NetworkResult.Error)?.message
                ?: (bannersResult.await() as? NetworkResult.Error)?.message

            _uiState.value = _uiState.value.copy(
                categories = categories,
                products = products,
                banners = banners,
                isLoading = false,
                error = error
            )
        }
    }
}
