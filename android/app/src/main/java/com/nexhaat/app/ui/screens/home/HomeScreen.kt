package com.nexhaat.app.ui.screens.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.CategoryCard
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductCard

@Composable
fun HomeScreen(
    viewModel: HomeViewModel = hiltViewModel(),
    onNavigateToCategories: () -> Unit,
    onNavigateToProducts: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToProductDetail: (Int) -> Unit,
    onNavigateToCart: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { MarketplaceTopBar(onSearch = onNavigateToSearch, onCart = onNavigateToCart) },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = MarketplaceTab.Home,
                onHome = {},
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        when {
            uiState.error != null && uiState.categories.isEmpty() && uiState.products.isEmpty() -> ErrorState(
                message = uiState.error ?: stringResource(R.string.error_occurred),
                onRetry = viewModel::loadHomeData,
                modifier = Modifier.padding(paddingValues)
            )
            else -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp)
                ) {
                    Column(modifier = Modifier.padding(top = 18.dp, bottom = 22.dp)) {
                        Text(
                            text = stringResource(R.string.marketplace_tagline),
                            color = MaterialTheme.colorScheme.primary,
                            style = MaterialTheme.typography.labelLarge
                        )
                        Spacer(modifier = Modifier.height(5.dp))
                        Text(
                            text = stringResource(R.string.home_headline),
                            style = MaterialTheme.typography.headlineSmall,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                    }
                    SectionHeading(
                        title = stringResource(R.string.shop_by_category),
                        actionLabel = stringResource(R.string.see_all),
                        onAction = onNavigateToCategories
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(uiState.categories, key = { it.id }) { category ->
                            CategoryCard(category = category, onClick = onNavigateToCategories)
                        }
                    }
                    Spacer(modifier = Modifier.height(24.dp))
                    SectionHeading(
                        title = stringResource(R.string.featured_products),
                        actionLabel = stringResource(R.string.see_all),
                        onAction = onNavigateToProducts
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    androidx.compose.foundation.lazy.grid.LazyVerticalGrid(
                        columns = GridCells.Adaptive(minSize = 156.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(560.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        contentPadding = PaddingValues(bottom = 18.dp)
                    ) {
                        items(uiState.products, key = { it.id }) { product ->
                            ProductCard(
                                product = product,
                                onClick = { onNavigateToProductDetail(product.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionHeading(
    title: String,
    actionLabel: String,
    onAction: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        androidx.compose.material3.TextButton(onClick = onAction) {
            Text(actionLabel)
        }
    }
}
