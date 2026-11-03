package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.data.remote.dto.SellerDashboardDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PortalRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getSellerDashboard(): NetworkResult<SellerDashboardDto> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getSellerDashboard()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to load seller metrics.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun getSellerOrders(): NetworkResult<List<OrderDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getSellerOrders()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to load seller orders.")
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
                    401 -> "Sign in as an approved seller to view seller portal."
                    403 -> "Approved seller permissions required."
                    else -> "Portal request failed (${error.code()})."
                }
                NetworkResult.Error(message, error.code().toString())
            }
            else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        }
    }
}
