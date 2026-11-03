package com.nexhaat.app.data.repository

import com.nexhaat.app.data.remote.ApiService
import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.AddCartItemRequest
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.remote.dto.UpdateCartItemRequest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CartRepository @Inject constructor(
    private val apiService: ApiService,
    private val authRepository: AuthRepository
) {
    suspend fun getCart(): NetworkResult<CartDto> = withContext(Dispatchers.IO) {
        request { apiService.getCart() }
    }

    suspend fun add(productId: Int, variantId: Int?, quantity: Int): NetworkResult<CartDto> =
        mutate { apiService.addCartItem(AddCartItemRequest(productId, variantId, quantity)) }

    suspend fun update(key: String, quantity: Int): NetworkResult<CartDto> =
        mutate { apiService.updateCartItem(key, UpdateCartItemRequest(quantity)) }

    suspend fun remove(key: String): NetworkResult<CartDto> = mutate { apiService.removeCartItem(key) }

    private suspend fun mutate(block: suspend () -> com.nexhaat.app.data.remote.dto.ApiResponse<CartDto>): NetworkResult<CartDto> =
        withContext(Dispatchers.IO) {
            if (!authRepository.ensureCsrfToken()) {
                return@withContext NetworkResult.Error("Could not start a secure session.")
            }
            request(block)
        }

    private suspend fun request(
        block: suspend () -> com.nexhaat.app.data.remote.dto.ApiResponse<CartDto>
    ): NetworkResult<CartDto> = try {
        val response = block()
        if (response.success && response.data != null) NetworkResult.Success(response.data)
        else NetworkResult.Error(response.error?.message ?: response.message ?: "Cart request failed.")
    } catch (error: CancellationException) {
        throw error
    } catch (error: Exception) {
        when (error) {
            is HttpException -> {
                val message = when (error.code()) {
                    401 -> "Sign in as a customer to use your cart."
                    403 -> "The shopping cart is only available to customer accounts."
                    else -> "Cart request failed (${error.code()})."
                }
                NetworkResult.Error(message, error.code().toString())
            }
            else -> NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        }
    }
}
