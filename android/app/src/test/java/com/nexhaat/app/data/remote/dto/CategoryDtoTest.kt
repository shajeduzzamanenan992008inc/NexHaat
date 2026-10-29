package com.nexhaat.app.data.remote.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CategoryDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun deserializeCategoryWithSnakeCaseIsActive() {
        val jsonString = """{"id":1,"name":"Food","slug":"food","description":null,"image":null,"is_active":true}"""
        val category = json.decodeFromString<CategoryDto>(jsonString)
        assertEquals(1, category.id)
        assertEquals("Food", category.name)
        assertEquals("food", category.slug)
        assertTrue(category.isActive)
    }
}
