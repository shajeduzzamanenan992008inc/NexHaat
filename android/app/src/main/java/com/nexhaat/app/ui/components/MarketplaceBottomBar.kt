package com.nexhaat.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ShoppingBag
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import com.nexhaat.app.R

enum class MarketplaceTab {
    Home,
    Categories,
    Deals,
    Orders,
    Search,
    Cart
}

@Composable
fun MarketplaceBottomBar(
    selectedTab: MarketplaceTab?,
    onHome: () -> Unit,
    onCategories: () -> Unit,
    onSearch: () -> Unit,
    onCart: () -> Unit = {},
    onDeals: () -> Unit = {},
    onOrders: () -> Unit = {}
) {
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        modifier = Modifier.testTag("marketplace_bottom_bar")
    ) {
        NavigationBarItem(
            selected = selectedTab == MarketplaceTab.Home,
            onClick = onHome,
            icon = { Icon(Icons.Default.Home, contentDescription = null) },
            label = { Text(stringResource(R.string.home)) },
            modifier = Modifier.testTag("nav_home"),
            colors = NavigationBarItemDefaults.colors(
                selectedIconColor = MaterialTheme.colorScheme.primary,
                selectedTextColor = MaterialTheme.colorScheme.primary,
                indicatorColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        NavigationBarItem(
            selected = selectedTab == MarketplaceTab.Categories,
            onClick = onCategories,
            icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = null) },
            label = { Text(stringResource(R.string.categories)) },
            modifier = Modifier.testTag("nav_categories"),
            colors = NavigationBarItemDefaults.colors(
                selectedIconColor = MaterialTheme.colorScheme.primary,
                selectedTextColor = MaterialTheme.colorScheme.primary,
                indicatorColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        NavigationBarItem(
            selected = selectedTab == MarketplaceTab.Deals,
            onClick = onDeals,
            icon = { Icon(Icons.Default.LocalOffer, contentDescription = null) },
            label = { Text(stringResource(R.string.deals)) },
            modifier = Modifier.testTag("nav_deals"),
            colors = NavigationBarItemDefaults.colors(
                selectedIconColor = MaterialTheme.colorScheme.primary,
                selectedTextColor = MaterialTheme.colorScheme.primary,
                indicatorColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        NavigationBarItem(
            selected = selectedTab == MarketplaceTab.Orders,
            onClick = onOrders,
            icon = { Icon(Icons.Default.ShoppingBag, contentDescription = null) },
            label = { Text(stringResource(R.string.orders)) },
            modifier = Modifier.testTag("nav_orders"),
            colors = NavigationBarItemDefaults.colors(
                selectedIconColor = MaterialTheme.colorScheme.primary,
                selectedTextColor = MaterialTheme.colorScheme.primary,
                indicatorColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
        NavigationBarItem(
            selected = selectedTab == MarketplaceTab.Cart,
            onClick = onCart,
            icon = { Icon(Icons.Default.ShoppingCart, contentDescription = null) },
            label = { Text(stringResource(R.string.cart)) },
            modifier = Modifier.testTag("nav_cart"),
            colors = NavigationBarItemDefaults.colors(
                selectedIconColor = MaterialTheme.colorScheme.primary,
                selectedTextColor = MaterialTheme.colorScheme.primary,
                indicatorColor = MaterialTheme.colorScheme.primaryContainer
            )
        )
    }
}
