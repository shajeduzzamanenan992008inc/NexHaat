package com.nexhaat.app.ui.screens.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SearchUiState(
    val products: List<ProductDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val query: String = ""
)

@HiltViewModel
class SearchViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(SearchUiState())
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()
    private var searchJob: Job? = null

    fun search(query: String, immediate: Boolean = false) {
        searchJob?.cancel()
        _uiState.value = _uiState.value.copy(query = query, error = null)
        if (query.isBlank()) {
            _uiState.value = _uiState.value.copy(products = emptyList(), isLoading = false)
            return
        }
        searchJob = viewModelScope.launch {
            if (!immediate) delay(300)
            val requestedQuery = query.trim()
            if (requestedQuery.isEmpty()) {
                _uiState.value = _uiState.value.copy(products = emptyList(), isLoading = false)
                return@launch
            }
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.searchProducts(requestedQuery)) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        products = result.data.first,
                        isLoading = false
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        error = result.message,
                        isLoading = false
                    )
                }
                NetworkResult.Loading -> {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }
            }
        }
    }

    fun clearSearch() {
        searchJob?.cancel()
        _uiState.value = SearchUiState()
    }
}
