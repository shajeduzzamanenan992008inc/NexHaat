package com.nexhaat.app.ui.screens.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductCard
import com.nexhaat.app.ui.components.ProductGridSkeleton

@Composable
fun SearchScreen(
    viewModel: SearchViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit = {},
    onNavigateToProductDetail: (Int) -> Unit,
    onNavigateToHome: () -> Unit = {},
    onNavigateToCategories: () -> Unit = {},
    onNavigateToCart: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { MarketplaceTopBar(onCart = onNavigateToCart) },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = MarketplaceTab.Search,
                onHome = onNavigateToHome,
                onCategories = onNavigateToCategories,
                onSearch = { },
                onCart = onNavigateToCart
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .imePadding()
                .padding(horizontal = 16.dp)
        ) {
            OutlinedTextField(
                value = uiState.query,
                onValueChange = viewModel::search,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
                placeholder = { Text(stringResource(R.string.search_hint)) },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (uiState.query.isNotEmpty()) {
                        IconButton(onClick = viewModel::clearSearch) {
                            Icon(
                                Icons.Default.Close,
                                contentDescription = stringResource(R.string.clear_search)
                            )
                        }
                    }
                },
                shape = RoundedCornerShape(16.dp),
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Text,
                    imeAction = ImeAction.Search
                ),
                keyboardActions = KeyboardActions(
                    onSearch = { viewModel.search(uiState.query, immediate = true) }
                ),
                singleLine = true
            )
            when {
                uiState.isLoading && uiState.products.isEmpty() -> ProductGridSkeleton(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(top = 16.dp),
                    cardHeight = 220.dp
                )
                (uiState.error != null || uiState.hasUnexpectedResult) && uiState.products.isEmpty() -> ErrorState(
                    message = uiState.error ?: stringResource(R.string.request_did_not_complete),
                    onRetry = { viewModel.search(uiState.query, immediate = true) },
                    modifier = Modifier.fillMaxSize()
                )
                uiState.query.isNotBlank() && uiState.products.isEmpty() && !uiState.isLoading ->
                    EmptyState(stringResource(R.string.no_products_found))
                uiState.query.isBlank() -> EmptyState(
                    stringResource(R.string.search_prompt)
                )
                else -> {
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(minSize = 156.dp),
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        contentPadding = PaddingValues(top = 16.dp, bottom = 20.dp)
                    ) {
                        item(span = { androidx.compose.foundation.lazy.grid.GridItemSpan(maxLineSpan) }) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
                            ) {
                                Text(
                                    text = stringResource(R.string.search_results_for, uiState.query),
                                    style = MaterialTheme.typography.titleLarge
                                )
                                if (uiState.isLoading) CircularProgressIndicator()
                            }
                        }
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
