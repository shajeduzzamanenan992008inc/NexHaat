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
}
