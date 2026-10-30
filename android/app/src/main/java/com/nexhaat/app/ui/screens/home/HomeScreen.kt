package com.nexhaat.app.ui.screens.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.nexhaat.app.R
import com.nexhaat.app.ui.components.CategoryCard
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductCard
import com.nexhaat.app.ui.components.ProductCardSkeleton
import com.nexhaat.app.ui.theme.NexHaatBlue
import com.nexhaat.app.ui.theme.NexHaatBlueDeep
import com.nexhaat.app.ui.theme.NexHaatOrange

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
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 156.dp),
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                MarketplaceHero(onExplore = onNavigateToProducts)
            }

            item(span = { GridItemSpan(maxLineSpan) }) {
                NexHaatBannerCarousel(
                    banners = uiState.banners,
                    modifier = Modifier.padding(top = 4.dp),
                    onBannerClick = { banner ->
                        when (banner.linkType?.lowercase()) {
                            "category" -> onNavigateToCategories()
                            "search" -> onNavigateToSearch()
                            else -> onNavigateToProducts()
                        }
                    }
                )
            }

            item(span = { GridItemSpan(maxLineSpan) }) {
                Column {
                    SectionHeading(
                        title = stringResource(R.string.shop_by_category),
                        actionLabel = stringResource(R.string.see_all),
                        onAction = onNavigateToCategories
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    if (uiState.categories.isEmpty()) {
                        Text(
                            text = stringResource(R.string.empty_categories),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            items(
                                count = uiState.categories.size,
                                key = { index -> uiState.categories[index].id }
                            ) { index ->
                                CategoryCard(
                                    category = uiState.categories[index],
                                    onClick = onNavigateToCategories
                                )
                            }
                        }
                    }
                }
            }

            item(span = { GridItemSpan(maxLineSpan) }) {
                SectionHeading(
                    title = stringResource(R.string.featured_products),
                    actionLabel = stringResource(R.string.see_all),
                    onAction = onNavigateToProducts
                )
            }

            when {
                uiState.isLoading && uiState.products.isEmpty() -> {
                    items(count = 6, key = { index -> "skeleton-$index" }) {
                        ProductCardSkeleton()
                    }
                }

                uiState.products.isEmpty() && uiState.error == null -> {
                    item(span = { GridItemSpan(maxLineSpan) }) {
                        Text(
                            text = stringResource(R.string.no_products_found),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 24.dp)
                        )
                    }
                }

                else -> {
                    items(items = uiState.products, key = { product -> product.id }) { product ->
                        ProductCard(
                            product = product,
                            onClick = { onNavigateToProductDetail(product.id) }
                        )
                    }
                }
            }

            uiState.error?.let { message ->
                item(span = { GridItemSpan(maxLineSpan) }) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(14.dp))
                            .background(MaterialTheme.colorScheme.errorContainer)
                            .padding(start = 14.dp, end = 6.dp, top = 4.dp, bottom = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = message,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            modifier = Modifier.weight(1f)
                        )
                        TextButton(onClick = viewModel::loadHomeData) {
                            Text(stringResource(R.string.retry))
                        }
                    }
                }
            }
        }
    }
}

/** Mirrors the website hero: eyebrow, two-line headline, supporting copy, one CTA. */
@Composable
private fun MarketplaceHero(onExplore: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Brush.linearGradient(listOf(NexHaatBlue, NexHaatBlueDeep)))
            .padding(20.dp)
    ) {
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .size(64.dp)
                .clip(CircleShape)
                .background(NexHaatOrange.copy(alpha = 0.9f))
        )
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "✦ " + stringResource(R.string.marketplace_tagline),
                style = MaterialTheme.typography.labelLarge,
                color = Color.White.copy(alpha = 0.92f)
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = stringResource(R.string.home_hero_line_one),
                style = MaterialTheme.typography.headlineSmall,
                color = Color.White
            )
            Text(
                text = stringResource(R.string.home_hero_line_two),
                style = MaterialTheme.typography.headlineSmall,
                color = Color.White
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.home_hero_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.88f),
                modifier = Modifier.padding(end = 56.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = onExplore,
                shape = RoundedCornerShape(999.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = NexHaatBlueDeep
                )
            ) {
                Text(
                    text = stringResource(R.string.explore_marketplace),
                    fontWeight = FontWeight.Bold
                )
            }
        }
        Image(
            painter = painterResource(R.drawable.logo),
            contentDescription = null,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 34.dp, end = 6.dp)
                .size(52.dp)
        )
    }
}

@Composable
private fun SectionHeading(
    title: String,
    actionLabel: String,
    onAction: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        TextButton(onClick = onAction) {
            Text(actionLabel)
        }
    }
}
