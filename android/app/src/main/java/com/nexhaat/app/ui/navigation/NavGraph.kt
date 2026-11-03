package com.nexhaat.app.ui.navigation

import android.widget.Toast
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.ui.screens.auth.SignInScreen
import com.nexhaat.app.ui.screens.auth.SessionViewModel
import com.nexhaat.app.ui.screens.cart.CartScreen
import com.nexhaat.app.ui.screens.catalog.CategoriesScreen
import com.nexhaat.app.ui.screens.home.HomeScreen
import com.nexhaat.app.ui.screens.product.ProductDetailScreen
import com.nexhaat.app.ui.screens.products.ProductsScreen
import com.nexhaat.app.ui.screens.search.SearchScreen
import com.nexhaat.app.ui.screens.settings.SettingsScreen
import com.nexhaat.app.data.session.SessionState


@Composable
fun NexHaatNavGraph() {
    val navController = rememberNavController()
    val sessionViewModel: SessionViewModel = hiltViewModel()
    val sessionState by sessionViewModel.sessionState.collectAsStateWithLifecycle()
    val isLoggingOut by sessionViewModel.isLoggingOut.collectAsStateWithLifecycle()
    val logoutError by sessionViewModel.logoutError.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var wasAuthenticated by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        sessionViewModel.revalidateSession()
    }
    LaunchedEffect(sessionState) {
        if (sessionState is SessionState.Authenticated) {
            wasAuthenticated = true
        } else if (sessionState is SessionState.Unauthenticated && wasAuthenticated) {
            wasAuthenticated = false
            navController.navigate(NavRoutes.Home.route) {
                popUpTo(NavRoutes.Home.route) { inclusive = false }
                launchSingleTop = true
            }
        }
    }
    LaunchedEffect(logoutError) {
        logoutError?.let {
            Toast.makeText(context, it, Toast.LENGTH_LONG).show()
            sessionViewModel.dismissLogoutError()
        }
    }

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
                onNavigateToCart = ::navigateToCart,
                onNavigateToSettings = { navController.navigate(NavRoutes.Settings.route) }
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
        composable(NavRoutes.Settings.route) {
            SettingsScreen(
                isLoggingOut = isLoggingOut,
                onLogout = sessionViewModel::logout,
                onNavigateBack = { navController.popBackStack() },
                onNavigateToHome = { navigateToTab(NavRoutes.Home.route) },
                onNavigateToCategories = { navigateToTab(NavRoutes.Categories.route) },
                onNavigateToSearch = { navigateToTab(NavRoutes.Search.route) },
                onNavigateToCart = ::navigateToCart
            )
        }
    }
}
