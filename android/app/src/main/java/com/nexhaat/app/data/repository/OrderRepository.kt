package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CheckoutPreviewRequest
import com.nexhaat.app.data.remote.dto.CheckoutPreviewResponse
import com.nexhaat.app.data.remote.dto.CheckoutRequest
import com.nexhaat.app.data.remote.dto.CheckoutResponse
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.data.remote.dto.ReturnOrderRequest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OrderRepository @Inject constructor(
    private val apiService: ApiService,
    private val authRepository: AuthRepository
) {
    suspend fun previewCheckout(promotionCode: String?): NetworkResult<CheckoutPreviewResponse> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.previewCheckout(CheckoutPreviewRequest(promotionCode))
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to preview checkout.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun checkout(request: CheckoutRequest): NetworkResult<CheckoutResponse> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.checkout(request)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Checkout could not be completed.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun getOrders(): NetworkResult<List<OrderDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getOrders()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch orders.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun getOrderDetail(orderNumber: String): NetworkResult<OrderDto> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getOrderDetail(orderNumber)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch order details.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun cancelOrder(orderNumber: String): NetworkResult<OrderDto> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.cancelOrder(orderNumber)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to cancel order.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun requestReturn(orderNumber: String, reason: String): NetworkResult<OrderDto> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.requestReturn(orderNumber, ReturnOrderRequest(reason))
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to submit return request.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    private fun <T> handleException(error: Exception): NetworkResult<T> {
        return when (error) {
            is HttpException -> {
                val message = when (error.code()) {
                    401 -> "Sign in as a customer to access orders."
                    404 -> "Order not found."
                    409 -> "Action cannot be performed on this order right now."
                    422 -> "Validation error. Please verify input."
                    else -> "Order request failed (${error.code()})."
                }
                NetworkResult.Error(message, error.code().toString())
            }
            else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        }
    }
}
