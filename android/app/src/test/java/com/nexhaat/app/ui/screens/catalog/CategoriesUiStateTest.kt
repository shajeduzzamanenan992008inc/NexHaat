package com.nexhaat.app.ui.screens.catalog

import com.nexhaat.app.data.remote.NetworkResult
import com.nexhaat.app.data.remote.dto.CategoryDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CategoriesUiStateTest {

    @Test
    fun successEndsLoadingAndStoresCategories() {
        val category = CategoryDto(id = 1, name = "Pantry", slug = "pantry")

        val state = CategoriesUiState(isLoading = true).withResult(
            NetworkResult.Success(listOf(category))
        )

        assertEquals(listOf(category), state.categories)
        assertFalse(state.isLoading)
        assertNull(state.error)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun emptySuccessEndsLoadingForEmptyState() {
        val state = CategoriesUiState(isLoading = true).withResult(
            NetworkResult.Success(emptyList())
        )

        assertTrue(state.categories.isEmpty())
        assertFalse(state.isLoading)
        assertNull(state.error)
    }

    @Test
    fun errorEndsLoadingAndPreservesError() {
        val state = CategoriesUiState(isLoading = true).withResult(
            NetworkResult.Error("Unavailable")
        )

        assertFalse(state.isLoading)
        assertEquals("Unavailable", state.error)
        assertFalse(state.hasUnexpectedResult)
    }

    @Test
    fun unexpectedLoadingResultEndsSpinnerAndEnablesErrorUi() {
        val state = CategoriesUiState(isLoading = true).withResult(NetworkResult.Loading)

        assertFalse(state.isLoading)
        assertTrue(state.hasUnexpectedResult)
    }
}
