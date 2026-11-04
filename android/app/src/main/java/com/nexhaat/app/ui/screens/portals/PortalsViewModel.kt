package com.nexhaat.app.ui.screens.portals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.data.remote.dto.SellerDashboardDto
import com.nexhaat.app.data.repository.PortalRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface PortalsUiState {
    object Loading : PortalsUiState
    data class Success(
        val dashboard: SellerDashboardDto,
        val orders: List<OrderDto>
    ) : PortalsUiState
    data class Error(val message: String) : PortalsUiState
}

@HiltViewModel
class PortalsViewModel @Inject constructor(
    private val portalRepository: PortalRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<PortalsUiState>(PortalsUiState.Loading)
    val uiState: StateFlow<PortalsUiState> = _uiState.asStateFlow()

    init {
        loadPortalData()
    }

    fun loadPortalData() {
        viewModelScope.launch {
            _uiState.value = PortalsUiState.Loading
            val dashboard = when (val result = portalRepository.getSellerDashboard()) {
                is NetworkResult.Success -> result.data
                is NetworkResult.Error -> {
                    _uiState.value = PortalsUiState.Error(result.message)
                    return@launch
                }
                NetworkResult.Loading -> {
                    _uiState.value = PortalsUiState.Error("Failed to load seller metrics.")
                    return@launch
                }
            }

            val orders = when (val result = portalRepository.getSellerOrders()) {
                is NetworkResult.Success -> result.data
                is NetworkResult.Error -> {
                    _uiState.value = PortalsUiState.Error(result.message)
                    return@launch
                }
                NetworkResult.Loading -> {
                    _uiState.value = PortalsUiState.Error("Failed to load seller orders.")
                    return@launch
                }
            }

            _uiState.value = PortalsUiState.Success(dashboard, orders)
        }
    }
}
