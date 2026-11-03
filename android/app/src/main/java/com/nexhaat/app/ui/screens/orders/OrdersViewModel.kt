package com.nexhaat.app.ui.screens.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.data.repository.OrderRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface OrdersUiState {
    object Loading : OrdersUiState
    data class Success(val orders: List<OrderDto>) : OrdersUiState
    data class Error(val message: String) : OrdersUiState
}

@HiltViewModel
class OrdersViewModel @Inject constructor(
    private val orderRepository: OrderRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<OrdersUiState>(OrdersUiState.Loading)
    val uiState: StateFlow<OrdersUiState> = _uiState.asStateFlow()

    private val _actionMessage = MutableStateFlow<String?>(null)
    val actionMessage: StateFlow<String?> = _actionMessage.asStateFlow()

    init {
        loadOrders()
    }

    fun loadOrders() {
        viewModelScope.launch {
            _uiState.value = OrdersUiState.Loading
            when (val result = orderRepository.getOrders()) {
                is NetworkResult.Success -> _uiState.value = OrdersUiState.Success(result.data)
                is NetworkResult.Error -> _uiState.value = OrdersUiState.Error(result.message)
            }
        }
    }

    fun cancelOrder(orderNumber: String) {
        viewModelScope.launch {
            when (val result = orderRepository.cancelOrder(orderNumber)) {
                is NetworkResult.Success -> {
                    _actionMessage.value = "Order #$orderNumber cancelled"
                    loadOrders()
                }
                is NetworkResult.Error -> _actionMessage.value = result.message
            }
        }
    }

    fun requestReturn(orderNumber: String, reason: String) {
        viewModelScope.launch {
            when (val result = orderRepository.requestReturn(orderNumber, reason)) {
                is NetworkResult.Success -> {
                    _actionMessage.value = "Return requested for Order #$orderNumber"
                    loadOrders()
                }
                is NetworkResult.Error -> _actionMessage.value = result.message
            }
        }
    }

    fun dismissActionMessage() {
        _actionMessage.value = null
    }
}
