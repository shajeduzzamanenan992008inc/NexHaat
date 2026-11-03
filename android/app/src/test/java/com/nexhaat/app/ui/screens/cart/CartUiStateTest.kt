package com.nexhaat.app.ui.screens.cart

import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CartDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CartUiStateTest {

    @Test
    fun successfulEmptyCartEndsLoading() {
        val cart = CartDto()

        val state = CartUiState(isLoading = true).withResult(NetworkResult.Success(cart))

        assertEquals(cart, state.cart)
        assertFalse(state.isLoading)
        assertNull(state.error)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun unauthenticatedResponseRequestsSignInAndEndsLoading() {
        val state = CartUiState(isLoading = true).withResult(
            NetworkResult.Error("Sign in as a customer to use your cart.", "401")
        )

        assertFalse(state.isLoading)
        assertEquals("401", state.errorCode)
        assertEquals("Sign in as a customer to use your cart.", state.error)
    }

    @Test
    fun recoverableNetworkErrorEndsLoadingWithoutSignInCode() {
        val state = CartUiState(isLoading = true).withResult(
            NetworkResult.Error("Unable to reach NexHaat. Check your connection.")
        )

        assertFalse(state.isLoading)
        assertNull(state.errorCode)
        assertEquals("Unable to reach NexHaat. Check your connection.", state.error)
    }

    @Test
    fun unexpectedLoadingResultEndsSpinnerAndEnablesRetryErrorUi() {
        val state = CartUiState(isLoading = true).withResult(NetworkResult.Loading)

        assertFalse(state.isLoading)
        assertTrue(state.hasUnexpectedResult)
    }
}
