package com.nexhaat.app.ui.navigation

sealed class NavRoutes(val route: String) {
    object Home : NavRoutes("home")
    object Categories : NavRoutes("categories")
    object Products : NavRoutes("products")
    object Search : NavRoutes("search")
    object ProductDetail : NavRoutes("product_detail/{productId}") {
        fun createRoute(productId: Int) = "product_detail/$productId"
    }
    object Cart : NavRoutes("cart")
    object SignIn : NavRoutes("sign_in")
    object Settings : NavRoutes("settings")
    object Deals : NavRoutes("deals")
    object Wishlist : NavRoutes("wishlist")
    object Notifications : NavRoutes("notifications")
    object Orders : NavRoutes("orders")
    object Checkout : NavRoutes("checkout")
    object OrderConfirmation : NavRoutes("order_confirmation/{orderNumber}") {
        fun createRoute(orderNumber: String) = "order_confirmation/$orderNumber"
    }
    object Portals : NavRoutes("portals")
    object SignUp : NavRoutes("sign_up")
    object VerifyRegistration : NavRoutes("verify_registration/{email}?challengeId={challengeId}") {
        fun createRoute(email: String, challengeId: String? = null) =
            if (challengeId != null) "verify_registration/$email?challengeId=$challengeId"
            else "verify_registration/$email"
    }
    object ForgotPassword : NavRoutes("forgot_password")
    object AIAssistant : NavRoutes("ai_assistant")
    object SecurityCenter : NavRoutes("security_center")
}
