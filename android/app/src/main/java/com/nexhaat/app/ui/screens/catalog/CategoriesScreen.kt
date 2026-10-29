package com.nexhaat.app.ui.screens.catalog

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
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
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.LoadingState
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar

@Composable
fun CategoriesScreen(
    viewModel: CategoriesViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit = {},
    onNavigateToProducts: (Int) -> Unit,
    onNavigateToHome: () -> Unit = {},
    onNavigateToSearch: () -> Unit = {},
    onNavigateToCart: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = { MarketplaceTopBar(onSearch = onNavigateToSearch, onCart = onNavigateToCart) },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = MarketplaceTab.Categories,
                onHome = onNavigateToHome,
                onCategories = { },
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.categories.isEmpty() -> LoadingState()
            uiState.error != null && uiState.categories.isEmpty() -> ErrorState(
                message = uiState.error ?: stringResource(R.string.error_occurred),
                onRetry = viewModel::loadCategories,
                modifier = Modifier.padding(paddingValues)
            )
            uiState.categories.isEmpty() -> EmptyState(
                message = stringResource(R.string.empty_categories),
                modifier = Modifier.padding(paddingValues)
            )
            else -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .padding(horizontal = 16.dp)
                ) {
                    Text(
                        text = stringResource(R.string.all_categories),
                        style = MaterialTheme.typography.headlineSmall,
                        modifier = Modifier.padding(top = 18.dp, bottom = 14.dp)
                    )
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(minSize = 156.dp),
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        contentPadding = PaddingValues(bottom = 20.dp)
                    ) {
                        items(uiState.categories, key = { it.id }) { category ->
                            CategoryCard(
                                category = category,
                                onClick = { onNavigateToProducts(category.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}
