package com.nexhaat.app.ui.screens.product

import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductDetailUiStateTest {

    @Test
    fun successEndsLoadingAndStoresProduct() {
        val product = ProductDto(id = 1, name = "Tea", slug = "tea")

        val state = ProductDetailUiState(isLoading = true).withProductResult(
            NetworkResult.Success(product)
        )

        assertEquals(product, state.product)
        assertFalse(state.isLoading)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun errorEndsLoadingAndPreservesMessage() {
        val state = ProductDetailUiState(isLoading = true).withProductResult(
            NetworkResult.Error("Unavailable")
        )

        assertFalse(state.isLoading)
        assertEquals("Unavailable", state.error)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun unexpectedLoadingResultEndsSpinnerAndEnablesErrorUi() {
        val state = ProductDetailUiState(isLoading = true).withProductResult(NetworkResult.Loading)

        assertFalse(state.isLoading)
        assertTrue(state.hasUnexpectedResult)
    }
}
