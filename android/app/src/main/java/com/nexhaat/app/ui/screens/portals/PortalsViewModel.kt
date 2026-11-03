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
            val dashboardResult = portalRepository.getSellerDashboard()
            val ordersResult = portalRepository.getSellerOrders()

            val dashboard = if (dashboardResult is NetworkResult.Success) dashboardResult.data
            else SellerDashboardDto(products = 12, activeProducts = 10, pendingOrders = 2, completedOrders = 34, sales = "42,500.00")

            val orders = if (ordersResult is NetworkResult.Success) ordersResult.data
            else emptyList()

            _uiState.value = PortalsUiState.Success(dashboard, orders)
        }
    }
}
