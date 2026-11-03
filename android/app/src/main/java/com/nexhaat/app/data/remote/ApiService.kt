package com.nexhaat.app.data.remote

import com.nexhaat.app.data.remote.dto.AIChatRequestDto
import com.nexhaat.app.data.remote.dto.AIChatResponseDto
import com.nexhaat.app.data.remote.dto.AddCartItemRequest
import com.nexhaat.app.data.remote.dto.AddWishlistRequest
import com.nexhaat.app.data.remote.dto.ApiResponse
import com.nexhaat.app.data.remote.dto.BannerDto
import com.nexhaat.app.data.remote.dto.CartDto
import com.nexhaat.app.data.remote.dto.CategoryDto
import com.nexhaat.app.data.remote.dto.CheckoutPreviewRequest
import com.nexhaat.app.data.remote.dto.CheckoutPreviewResponse
import com.nexhaat.app.data.remote.dto.CheckoutRequest
import com.nexhaat.app.data.remote.dto.CheckoutResponse
import com.nexhaat.app.data.remote.dto.CsrfTokenDto
import com.nexhaat.app.data.remote.dto.ForgotPasswordRequestDto
import com.nexhaat.app.data.remote.dto.LoginRequestDto
import com.nexhaat.app.data.remote.dto.NotificationListDto
import com.nexhaat.app.data.remote.dto.OrderDto
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.remote.dto.RegisterRequestDto
import com.nexhaat.app.data.remote.dto.RegistrationChallengeDto
import com.nexhaat.app.data.remote.dto.ResetPasswordRequestDto
import com.nexhaat.app.data.remote.dto.ReturnOrderRequest
import com.nexhaat.app.data.remote.dto.SellerDashboardDto
import com.nexhaat.app.data.remote.dto.SocialLoginRequestDto
import com.nexhaat.app.data.remote.dto.TotpSetupDto
import com.nexhaat.app.data.remote.dto.TotpVerifyRequestDto
import com.nexhaat.app.data.remote.dto.UpdateCartItemRequest
import com.nexhaat.app.data.remote.dto.UserDto
import com.nexhaat.app.data.remote.dto.VerifyRegistrationRequestDto
import com.nexhaat.app.data.remote.dto.WishlistActionDto
import com.nexhaat.app.data.remote.dto.WishlistResponseDto
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

    @POST("api/v1/auth/register")
    suspend fun register(@Body request: RegisterRequestDto): ApiResponse<RegistrationChallengeDto>

    @POST("api/v1/auth/register/verify")
    suspend fun verifyRegistration(@Body request: VerifyRegistrationRequestDto): ApiResponse<UserDto>

    @POST("api/v1/auth/forgot-password")
    suspend fun forgotPassword(@Body request: ForgotPasswordRequestDto): ApiResponse<JsonElement>

    @POST("api/v1/auth/reset-password")
    suspend fun resetPassword(@Body request: ResetPasswordRequestDto): ApiResponse<JsonElement>

    @POST("api/v1/auth/social-login")
    suspend fun socialLogin(@Body request: SocialLoginRequestDto): ApiResponse<UserDto>

    @POST("api/v1/auth/2fa/setup")
    suspend fun setupTotp(): ApiResponse<TotpSetupDto>

    @POST("api/v1/auth/2fa/verify")
    suspend fun verifyTotp(@Body request: TotpVerifyRequestDto): ApiResponse<JsonElement>

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

    @GET("api/v1/banners")
    suspend fun getBanners(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 10
    ): ApiResponse<List<BannerDto>>

    // Wishlist API
    @GET("api/v1/wishlist")
    suspend fun getWishlist(): ApiResponse<WishlistResponseDto>

    @POST("api/v1/wishlist/items")
    suspend fun addWishlistItem(@Body request: AddWishlistRequest): ApiResponse<WishlistActionDto>

    @DELETE("api/v1/wishlist/items/{productId}")
    suspend fun removeWishlistItem(@Path("productId") productId: Int): ApiResponse<WishlistActionDto>

    // Notifications API
    @GET("api/v1/notifications")
    suspend fun getNotifications(): ApiResponse<NotificationListDto>

    @POST("api/v1/notifications/read-all")
    suspend fun markAllNotificationsRead(): ApiResponse<JsonElement>

    @POST("api/v1/notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") id: Int): ApiResponse<JsonElement>

    // Checkout and Orders API
    @POST("api/v1/checkout/preview")
    suspend fun previewCheckout(@Body request: CheckoutPreviewRequest): ApiResponse<CheckoutPreviewResponse>

    @POST("api/v1/checkout")
    suspend fun checkout(@Body request: CheckoutRequest): ApiResponse<CheckoutResponse>

    @GET("api/v1/orders")
    suspend fun getOrders(): ApiResponse<List<OrderDto>>

    @GET("api/v1/orders/{orderNumber}")
    suspend fun getOrderDetail(@Path("orderNumber") orderNumber: String): ApiResponse<OrderDto>

    @POST("api/v1/orders/{orderNumber}/cancel")
    suspend fun cancelOrder(@Path("orderNumber") orderNumber: String): ApiResponse<OrderDto>

    @POST("api/v1/orders/{orderNumber}/return")
    suspend fun requestReturn(
        @Path("orderNumber") orderNumber: String,
        @Body request: ReturnOrderRequest
    ): ApiResponse<OrderDto>

    // Seller Portal API
    @GET("api/v1/seller/dashboard")
    suspend fun getSellerDashboard(): ApiResponse<SellerDashboardDto>

    @GET("api/v1/seller/orders")
    suspend fun getSellerOrders(): ApiResponse<List<OrderDto>>

    // AI Chat API
    @POST("api/gemini/chat")
    suspend fun chatWithAI(@Body request: AIChatRequestDto): AIChatResponseDto
}
