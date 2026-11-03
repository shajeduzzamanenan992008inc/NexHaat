package com.nexhaat.app.ui.screens.checkout

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.remote.dto.CheckoutPreviewResponse
import com.nexhaat.app.data.remote.dto.CheckoutRequest
import com.nexhaat.app.data.remote.dto.CheckoutResponse
import com.nexhaat.app.data.repository.CartRepository
import com.nexhaat.app.data.repository.OrderRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface CheckoutUiState {
    object Loading : CheckoutUiState
    data class Ready(
        val cart: CartDto,
        val preview: CheckoutPreviewResponse? = null,
        val isPlacingOrder: Boolean = false,
        val error: String? = null
    ) : CheckoutUiState
    data class Completed(val orderNumber: String, val checkoutResponse: CheckoutResponse) : CheckoutUiState
    data class Error(val message: String) : CheckoutUiState
}

@HiltViewModel
class CheckoutViewModel @Inject constructor(
    private val cartRepository: CartRepository,
    private val orderRepository: OrderRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<CheckoutUiState>(CheckoutUiState.Loading)
    val uiState: StateFlow<CheckoutUiState> = _uiState.asStateFlow()

    private var currentCart: CartDto? = null
    private var currentPreview: CheckoutPreviewResponse? = null

    init {
        loadCheckoutData()
    }

    fun loadCheckoutData() {
        viewModelScope.launch {
            _uiState.value = CheckoutUiState.Loading
            when (val cartResult = cartRepository.getCart()) {
                is NetworkResult.Success -> {
                    currentCart = cartResult.data
                    previewDiscount(null)
                }
                is NetworkResult.Error -> {
                    _uiState.value = CheckoutUiState.Error(cartResult.message)
                }
            }
        }
    }

    fun previewDiscount(promoCode: String?) {
        val cart = currentCart ?: return
        viewModelScope.launch {
            when (val previewResult = orderRepository.previewCheckout(promoCode)) {
                is NetworkResult.Success -> {
                    currentPreview = previewResult.data
                    _uiState.value = CheckoutUiState.Ready(
                        cart = cart,
                        preview = previewResult.data
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = CheckoutUiState.Ready(
                        cart = cart,
                        preview = currentPreview,
                        error = if (promoCode != null) previewResult.message else null
                    )
                }
            }
        }
    }

    fun placeOrder(
        customerName: String,
        phone: String,
        address: String,
        city: String,
        paymentMethod: String,
        promoCode: String?
    ) {
        val cart = currentCart ?: return
        viewModelScope.launch {
            _uiState.value = CheckoutUiState.Ready(
                cart = cart,
                preview = currentPreview,
                isPlacingOrder = true
            )

            val request = CheckoutRequest(
                customerName = customerName.trim(),
                phone = phone.trim(),
                address = address.trim(),
                city = city.trim(),
                paymentMethod = paymentMethod,
                promotionCode = promoCode?.trim()?.ifBlank { null }
            )

            when (val result = orderRepository.checkout(request)) {
                is NetworkResult.Success -> {
                    val firstOrderNumber = result.data.orders.firstOrNull()?.orderNumber ?: "NEX-${System.currentTimeMillis() % 100000}"
                    _uiState.value = CheckoutUiState.Completed(
                        orderNumber = firstOrderNumber,
                        checkoutResponse = result.data
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = CheckoutUiState.Ready(
                        cart = cart,
                        preview = currentPreview,
                        isPlacingOrder = false,
                        error = result.message
                    )
                }
            }
        }
    }
}
