package com.nexhaat.app.ui.screens.search

import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.ProductDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchUiStateTest {

    @Test
    fun successStoresResultsForRequestedQuery() {
        val product = ProductDto(id = 1, name = "Tea", slug = "tea")

        val state = SearchUiState(isLoading = true).withResult(
            NetworkResult.Success(listOf(product) to null),
            requestedQuery = "tea"
        )

        assertEquals(listOf(product), state.products)
        assertEquals("tea", state.query)
        assertFalse(state.isLoading)
    }

    @Test
    fun errorClearsStaleResultsForPreviousQuery() {
        val state = SearchUiState(
            products = listOf(ProductDto(id = 1, name = "Tea", slug = "tea")),
            isLoading = true
        ).withResult(NetworkResult.Error("Unavailable"), requestedQuery = "coffee")

        assertTrue(state.products.isEmpty())
        assertEquals("Unavailable", state.error)
        assertEquals("coffee", state.query)
        assertFalse(state.isLoading)
    }

    @Test
    fun unexpectedLoadingResultEndsSpinner() {
        val state = SearchUiState(isLoading = true).withResult(
            NetworkResult.Loading,
            requestedQuery = "tea"
        )

        assertTrue(state.hasUnexpectedResult)
        assertFalse(state.isLoading)
    }
}
