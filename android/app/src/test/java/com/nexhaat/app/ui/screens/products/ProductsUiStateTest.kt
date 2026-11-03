package com.nexhaat.app.ui.screens.products

import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductsUiStateTest {

    @Test
    fun successfulEmptyPageEndsLoadingAndExhaustsList() {
        val state = ProductsUiState(isLoading = true).withResult(
            NetworkResult.Success(emptyList<ProductDto>() to null),
            page = 1,
            refresh = true
        )

        assertFalse(state.isLoading)
        assertTrue(state.products.isEmpty())
        assertFalse(state.hasMore)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun errorEndsLoadingAndPreservesCurrentProducts() {
        val product = ProductDto(id = 1, name = "Tea", slug = "tea")
        val state = ProductsUiState(products = listOf(product), isLoading = true).withResult(
            NetworkResult.Error("Unavailable"),
            page = 2,
            refresh = false
        )

        assertFalse(state.isLoading)
        assertEquals(listOf(product), state.products)
        assertEquals("Unavailable", state.error)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun unexpectedLoadingResultEndsSpinnerAndEnablesErrorUi() {
        val state = ProductsUiState(isLoading = true).withResult(
            NetworkResult.Loading,
            page = 1,
            refresh = true
        )

        assertFalse(state.isLoading)
        assertTrue(state.hasUnexpectedResult)
    }
}
