package com.nexhaat.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.nexhaat.app.ui.screens.auth.SignInScreen
import com.nexhaat.app.ui.screens.cart.CartScreen
import com.nexhaat.app.ui.screens.catalog.CategoriesScreen
import com.nexhaat.app.ui.screens.home.HomeScreen
import com.nexhaat.app.ui.screens.product.ProductDetailScreen
import com.nexhaat.app.ui.screens.products.ProductsScreen
import com.nexhaat.app.ui.screens.search.SearchScreen

@Composable
fun NexHaatNavGraph() {
    val navController = rememberNavController()

    fun navigateToTab(route: String) {
        navController.navigate(route) {
            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    fun navigateToProduct(productId: Int) {
        navController.navigate(NavRoutes.ProductDetail.createRoute(productId))
    }

    fun navigateToCart() {
        navController.navigate(NavRoutes.Cart.route) { launchSingleTop = true }
    }

    NavHost(
        navController = navController,
        startDestination = NavRoutes.Home.route
    ) {
        composable(NavRoutes.Home.route) {
            HomeScreen(
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToProducts = { navController.navigate(NavRoutes.Products.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToProductDetail = ::navigateToProduct,
                onNavigateToCart = ::navigateToCart
            )
        }
        composable(NavRoutes.Categories.route) {
            CategoriesScreen(
                onNavigateToProducts = { categoryId ->
                    navController.navigate("${NavRoutes.Products.route}?categoryId=$categoryId")
                },
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToCart = ::navigateToCart
            )
        }
        composable(
            route = "${NavRoutes.Products.route}?categoryId={categoryId}",
            arguments = listOf(navArgument("categoryId") {
                type = NavType.IntType
                defaultValue = -1
            })
        ) { backStackEntry ->
            val categoryId = backStackEntry.arguments?.getInt("categoryId") ?: -1
            ProductsScreen(
                categoryId = if (categoryId == -1) null else categoryId,
                onNavigateToProductDetail = ::navigateToProduct,
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToCart = ::navigateToCart
            )
        }
        composable(NavRoutes.Search.route) {
            SearchScreen(
                onNavigateToProductDetail = ::navigateToProduct,
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToCart = ::navigateToCart
            )
        }
        composable(
            route = NavRoutes.ProductDetail.route,
            arguments = listOf(navArgument("productId") { type = NavType.IntType })
        ) { backStackEntry ->
            val productId = backStackEntry.arguments?.getInt("productId") ?: 0
            ProductDetailScreen(
                productId = productId,
                onNavigateBack = { navController.popBackStack() },
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToCart = ::navigateToCart
            )
        }
        composable(NavRoutes.Cart.route) {
            CartScreen(
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToSignIn = { navController.navigate(NavRoutes.SignIn.route) }
            )
        }
        composable(NavRoutes.SignIn.route) {
            SignInScreen(
                onNavigateBack = { navController.popBackStack() },
                onSignedIn = {
                    navController.navigate(NavRoutes.Cart.route) {
                        popUpTo(NavRoutes.SignIn.route) { inclusive = true }
                        launchSingleTop = true
                    }
                }
            )
        }
    }
}
