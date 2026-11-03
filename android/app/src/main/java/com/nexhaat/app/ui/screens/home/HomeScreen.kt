package com.nexhaat.app.ui.screens.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BusinessCenter
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.ShoppingBag
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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
    onNavigateToCart: () -> Unit = {},
    onNavigateToSettings: (() -> Unit)? = null,
    onNavigateToDeals: () -> Unit = {},
    onNavigateToWishlist: () -> Unit = {},
    onNavigateToNotifications: () -> Unit = {},
    onNavigateToOrders: () -> Unit = {},
    onNavigateToPortals: () -> Unit = {},
    onNavigateToAIAssistant: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            MarketplaceTopBar(
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart,
                onSettings = onNavigateToSettings,
                onWishlist = onNavigateToWishlist,
                onNotifications = onNavigateToNotifications
            )
        },
        floatingActionButton = {
            androidx.compose.material3.FloatingActionButton(
                onClick = onNavigateToAIAssistant,
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("ai_assistant_fab")
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = androidx.compose.material.icons.Icons.Default.AutoAwesome,
                        contentDescription = stringResource(R.string.ai_assistant)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = stringResource(R.string.ai_assistant),
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.labelLarge
                    )
                }
            }
        },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = MarketplaceTab.Home,
                onHome = {},
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart,
                onDeals = onNavigateToDeals,
                onOrders = onNavigateToOrders
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 156.dp),
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .testTag("home_screen_grid"),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item(span = { GridItemSpan(maxLineSpan) }) {
                MarketplaceHero(onExplore = onNavigateToProducts)
            }

            // Quick Hub Shortcuts
            item(span = { GridItemSpan(maxLineSpan) }) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    QuickActionChip(
                        title = stringResource(R.string.deals),
                        icon = Icons.Default.LocalOffer,
                        color = MaterialTheme.colorScheme.primary,
                        onClick = onNavigateToDeals,
                        modifier = Modifier.weight(1f),
                        testTag = "home_quick_deals"
                    )
                    QuickActionChip(
                        title = stringResource(R.string.wishlist),
                        icon = Icons.Default.Favorite,
                        color = MaterialTheme.colorScheme.error,
                        onClick = onNavigateToWishlist,
                        modifier = Modifier.weight(1f),
                        testTag = "home_quick_wishlist"
                    )
                    QuickActionChip(
                        title = stringResource(R.string.orders),
                        icon = Icons.Default.ShoppingBag,
                        color = MaterialTheme.colorScheme.secondary,
                        onClick = onNavigateToOrders,
                        modifier = Modifier.weight(1f),
                        testTag = "home_quick_orders"
                    )
                    QuickActionChip(
                        title = "Portals",
                        icon = Icons.Default.BusinessCenter,
                        color = MaterialTheme.colorScheme.tertiary,
                        onClick = onNavigateToPortals,
                        modifier = Modifier.weight(1f),
                        testTag = "home_quick_portals"
                    )
                }
            }

            item(span = { GridItemSpan(maxLineSpan) }) {
                NexHaatBannerCarousel(
                    banners = uiState.banners,
                    modifier = Modifier.padding(top = 4.dp),
                    onBannerClick = { banner ->
                        when (banner.linkType?.lowercase()) {
                            "category" -> onNavigateToCategories()
                            "search" -> onNavigateToSearch()
                            "deal" -> onNavigateToDeals()
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

@Composable
private fun QuickActionChip(
    title: String,
    icon: ImageVector,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    testTag: String = ""
) {
    Card(
        modifier = modifier
            .clickable(onClick = onClick)
            .testTag(testTag),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 12.dp, horizontal = 4.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier.size(20.dp)
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                maxLines = 1
            )
        }
    }
}

@Composable
private fun MarketplaceHero(onExplore: () -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("marketplace_hero"),
        shape = RoundedCornerShape(20.dp),
        shadowElevation = 4.dp,
        color = MaterialTheme.colorScheme.surface
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            NexHaatBlue.copy(alpha = 0.08f),
                            NexHaatOrange.copy(alpha = 0.08f)
                        )
                    )
                )
                .padding(20.dp)
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = stringResource(R.string.home_hero_line_one),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = NexHaatBlueDeep
                        )
                        Text(
                            text = stringResource(R.string.home_hero_line_two),
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.ExtraBold,
                            color = NexHaatOrange
                        )
                    }
                    Image(
                        painter = painterResource(R.drawable.logo),
                        contentDescription = stringResource(R.string.app_name),
                        modifier = Modifier.size(54.dp)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = stringResource(R.string.home_hero_subtitle),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(14.dp))

                Button(
                    onClick = onExplore,
                    modifier = Modifier.testTag("hero_explore_button"),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NexHaatBlue)
                ) {
                    Text(
                        text = stringResource(R.string.explore_marketplace),
                        fontWeight = FontWeight.Bold
                    )
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
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold
        )
        TextButton(onClick = onAction) {
            Text(actionLabel, fontWeight = FontWeight.SemiBold)
        }
    }
}
