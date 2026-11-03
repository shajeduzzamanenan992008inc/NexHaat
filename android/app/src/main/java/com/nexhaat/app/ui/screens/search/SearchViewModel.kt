package com.nexhaat.app.ui.screens.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
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
    val query: String = "",
    val hasUnexpectedResult: Boolean = false
)

internal fun SearchUiState.withResult(
    result: NetworkResult<Pair<List<ProductDto>, com.nexhaat.app.data.remote.dto.Pagination?>>,
    requestedQuery: String
): SearchUiState = when (result) {
    is NetworkResult.Success -> copy(
        products = result.data.first,
        isLoading = false,
        error = null,
        query = requestedQuery,
        hasUnexpectedResult = false
    )
    is NetworkResult.Error -> copy(
        products = emptyList(),
        isLoading = false,
        error = result.message,
        query = requestedQuery,
        hasUnexpectedResult = false
    )
    NetworkResult.Loading -> copy(
        products = emptyList(),
        isLoading = false,
        error = null,
        query = requestedQuery,
        hasUnexpectedResult = true
    )
}

@HiltViewModel
class SearchViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(SearchUiState())
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()
    private var searchJob: Job? = null

    fun search(query: String, immediate: Boolean = false) {
        searchJob?.cancel()
        if (query.isBlank()) {
            _uiState.value = SearchUiState()
            return
        }
        _uiState.value = SearchUiState(query = query, isLoading = true)
        searchJob = viewModelScope.launch {
            if (!immediate) delay(300)
            val requestedQuery = query.trim()
            if (requestedQuery.isEmpty()) {
                _uiState.value = SearchUiState()
                return@launch
            }
            try {
                _uiState.value = _uiState.value.withResult(
                    repository.searchProducts(requestedQuery),
                    requestedQuery
                )
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                _uiState.value = SearchUiState(
                    isLoading = false,
                    query = requestedQuery,
                    hasUnexpectedResult = true
                )
            }
        }
    }

    fun clearSearch() {
        searchJob?.cancel()
        _uiState.value = SearchUiState()
    }
}
