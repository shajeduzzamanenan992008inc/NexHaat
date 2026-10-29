package com.nexhaat.app.data.remote

import com.nexhaat.app.data.remote.dto.AddCartItemRequest
import com.nexhaat.app.data.remote.dto.ApiResponse
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.remote.dto.CsrfTokenDto
import com.nexhaat.app.data.remote.dto.LoginRequestDto
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.remote.dto.UpdateCartItemRequest
import com.nexhaat.app.data.remote.dto.UserDto
import kotlinx.serialization.json.JsonElement
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("api/v1/auth/csrf")
    suspend fun getCsrfToken(): ApiResponse<CsrfTokenDto>

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequestDto): ApiResponse<UserDto>

    @POST("api/v1/auth/logout")
    suspend fun logout(): ApiResponse<JsonElement>

    @GET("api/v1/auth/me")
    suspend fun getCurrentUser(): ApiResponse<UserDto>

    @GET("api/v1/cart")
    suspend fun getCart(): ApiResponse<CartDto>

    @POST("api/v1/cart/items")
    suspend fun addCartItem(@Body request: AddCartItemRequest): ApiResponse<CartDto>

    @PATCH("api/v1/cart/items/{cartKey}")
    suspend fun updateCartItem(
        @Path("cartKey", encoded = true) cartKey: String,
        @Body request: UpdateCartItemRequest
    ): ApiResponse<CartDto>

    @DELETE("api/v1/cart/items/{cartKey}")
    suspend fun removeCartItem(@Path("cartKey", encoded = true) cartKey: String): ApiResponse<CartDto>

    @GET("api/v1/categories")
    suspend fun getCategories(): ApiResponse<List<CategoryDto>>

    @GET("api/v1/products")
    suspend fun getProducts(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
        @Query("q") query: String? = null,
        @Query("category_id") categoryId: Int? = null,
        @Query("sort") sort: String? = null,
        @Query("min_price") minPrice: String? = null,
        @Query("max_price") maxPrice: String? = null
    ): ApiResponse<List<ProductDto>>

    @GET("api/v1/products")
    suspend fun getCategoryProducts(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
        @Query("category_id") categoryId: Int,
        @Query("sort") sort: String? = null
    ): ApiResponse<List<ProductDto>>

    @GET("api/v1/search")
    suspend fun searchProducts(
        @Query("q") query: String,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20
    ): ApiResponse<List<ProductDto>>

    @GET("api/v1/products/{id}")
    suspend fun getProductDetail(@Path("id") productId: Int): ApiResponse<ProductDto>
}
