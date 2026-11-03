package com.nexhaat.app.ui.screens.catalog

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.repository.CatalogRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CategoriesUiState(
    val categories: List<CategoryDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val hasUnexpectedResult: Boolean = false
)

internal fun CategoriesUiState.withResult(
    result: NetworkResult<List<CategoryDto>>
): CategoriesUiState = when (result) {
    is NetworkResult.Success -> copy(
        categories = result.data,
        isLoading = false,
        error = null,
        hasUnexpectedResult = false
    )
    is NetworkResult.Error -> copy(
        error = result.message,
        isLoading = false,
        hasUnexpectedResult = false
    )
    NetworkResult.Loading -> copy(
        isLoading = false,
        error = null,
        hasUnexpectedResult = true
    )
}

@HiltViewModel
class CategoriesViewModel @Inject constructor(
    private val repository: CatalogRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(CategoriesUiState())
    val uiState: StateFlow<CategoriesUiState> = _uiState.asStateFlow()
    private var categoriesJob: Job? = null

    init {
        loadCategories()
    }

    fun loadCategories() {
        if (categoriesJob?.isActive == true) return
        categoriesJob = viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                hasUnexpectedResult = false
            )
            try {
                _uiState.value = _uiState.value.withResult(repository.getCategories())
            } catch (error: CancellationException) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = null,
                    hasUnexpectedResult = false
                )
                throw error
            } catch (_: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = null,
                    hasUnexpectedResult = true
                )
            } finally {
                if (_uiState.value.isLoading) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = null,
                        hasUnexpectedResult = true
                    )
                }
            }
        }
    }
}
