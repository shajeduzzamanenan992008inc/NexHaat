package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.AddWishlistRequest
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.remote.dto.WishlistActionDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WishlistRepository @Inject constructor(
    private val apiService: ApiService,
    private val authRepository: AuthRepository
) {
    suspend fun getWishlist(): NetworkResult<List<ProductDto>> = withContext(Dispatchers.IO) {
        try {
            val response = apiService.getWishlist()
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data.products)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to fetch wishlist.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun add(productId: Int): NetworkResult<WishlistActionDto> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.addWishlistItem(AddWishlistRequest(productId))
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to save item.")
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: Exception) {
            handleException(error)
        }
    }

    suspend fun remove(productId: Int): NetworkResult<WishlistActionDto> = withContext(Dispatchers.IO) {
        if (!authRepository.ensureCsrfToken()) {
            return@withContext NetworkResult.Error("Could not start a secure session.")
        }
        try {
            val response = apiService.removeWishlistItem(productId)
            if (response.success && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.error?.message ?: response.message ?: "Failed to remove item.")
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
                    401 -> "Sign in as a customer to access your wishlist."
                    403 -> "Wishlist is only available for customer accounts."
                    else -> "Wishlist request failed (${error.code()})."
                }
                NetworkResult.Error(message, error.code().toString())
            }
            else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        }
    }
}
