package com.nexhaat.app.ui.screens.products

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductCard
import com.nexhaat.app.ui.components.ProductGridSkeleton

@Composable
fun ProductsScreen(
    viewModel: ProductsViewModel = hiltViewModel(),
    categoryId: Int? = null,
    query: String? = null,
    onNavigateBack: () -> Unit = {},
    onNavigateToProductDetail: (Int) -> Unit,
    onNavigateToCategories: () -> Unit = {},
    onNavigateToHome: () -> Unit = {},
    onNavigateToSearch: () -> Unit = {},
    onNavigateToCart: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(categoryId, query) {
        viewModel.loadProducts(categoryId = categoryId, query = query, refresh = true)
    }

    Scaffold(
        topBar = { MarketplaceTopBar(onSearch = onNavigateToSearch, onCart = onNavigateToCart) },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = null,
                onHome = onNavigateToHome,
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.products.isEmpty() -> ProductGridSkeleton(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 16.dp),
                cardHeight = 220.dp
            )
            uiState.error != null && uiState.products.isEmpty() -> ErrorState(
                message = uiState.error ?: stringResource(R.string.error_occurred),
                onRetry = { viewModel.loadProducts(categoryId = categoryId, query = query, refresh = true) },
                modifier = Modifier.padding(paddingValues)
            )
            uiState.products.isEmpty() -> EmptyState(
                message = stringResource(R.string.no_products_found),
                modifier = Modifier.padding(paddingValues)
            )
            else -> {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 156.dp),
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),

                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(16.dp)
                ) {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Text(
                            text = query?.takeIf(String::isNotBlank)
                                ?.let { stringResource(R.string.search_results_for, it) }
                                ?: stringResource(R.string.products),
                            style = MaterialTheme.typography.headlineSmall,
                            modifier = Modifier.padding(bottom = 2.dp)
                        )
                    }
                    items(uiState.products, key = { it.id }) { product ->
                        ProductCard(
                            product = product,
                            onClick = { onNavigateToProductDetail(product.id) }
                        )
                    }
                    if (uiState.isLoading) {
                        item(span = { GridItemSpan(maxLineSpan) }) {
                            CircularProgressIndicator(
                                modifier = Modifier.padding(18.dp)
                            )
                        }
                    } else if (uiState.hasMore) {
                        item(span = { GridItemSpan(maxLineSpan) }) {
                            TextButton(
                                onClick = { viewModel.loadMore(categoryId = categoryId, query = query) },
                                modifier = Modifier.padding(vertical = 8.dp)
                            ) {
                                Text(stringResource(R.string.load_more))
                            }
                        }
                    }
                }
            }
        }
    }
}
