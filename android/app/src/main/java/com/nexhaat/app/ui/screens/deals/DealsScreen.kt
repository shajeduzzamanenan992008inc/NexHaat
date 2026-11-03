package com.nexhaat.app.ui.screens.deals

import android.widget.Toast
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddShoppingCart
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.LoadingState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductImage

@Composable
fun DealsScreen(
    viewModel: DealsViewModel = hiltViewModel(),
    onNavigateToProductDetail: (Int) -> Unit,
    onNavigateToHome: () -> Unit,
    onNavigateToCategories: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToCart: () -> Unit,
    onNavigateToSettings: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val actionMessage by viewModel.actionMessage.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(actionMessage) {
        actionMessage?.let {
            Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
            viewModel.dismissActionMessage()
        }
    }

    Scaffold(
        topBar = {
            MarketplaceTopBar(
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart,
                onSettings = onNavigateToSettings
            )
        },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = null,
                onHome = onNavigateToHome,
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = onNavigateToCart
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (val state = uiState) {
                is DealsUiState.Loading -> LoadingState()
                is DealsUiState.Error -> ErrorState(
                    message = state.message,
                    onRetry = viewModel::loadDeals
                )
                is DealsUiState.Success -> {
                    if (state.deals.isEmpty()) {
                        EmptyState(
                            title = stringResource(R.string.no_products_found),
                            message = stringResource(R.string.search_prompt),
                            buttonText = stringResource(R.string.explore_marketplace),
                            onButtonClick = onNavigateToHome
                        )
                    } else {
                        DealsList(
                            deals = state.deals,
                            onProductClick = onNavigateToProductDetail,
                            onAddToCart = viewModel::addToCart
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DealsList(
    deals: List<ProductDto>,
    onProductClick: (Int) -> Unit,
    onAddToCart: (ProductDto) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("deals_list"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            DealsHeroBanner()
        }
        items(deals, key = { it.id }) { product ->
            DealProductCard(
                product = product,
                onClick = { onProductClick(product.id) },
                onAddToCart = { onAddToCart(product) }
            )
        }
    }
}

@Composable
private fun DealsHeroBanner() {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("deals_hero_banner"),
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.primaryContainer,
        shadowElevation = 2.dp
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.LocalOffer,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = stringResource(R.string.flash_deals),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.deals_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
            )
            Spacer(modifier = Modifier.height(10.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.primary)
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Timer,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(16.dp)
                )
                Text(
                    text = "Limited Time Offer • Save up to 50%",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onPrimary
                )
            }
        }
    }
}

@Composable
private fun DealProductCard(
    product: ProductDto,
    onClick: () -> Unit,
    onAddToCart: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag("deal_card_${product.id}"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(96.dp)
                    .clip(RoundedCornerShape(10.dp))
            ) {
                ProductImage(
                    imageReference = product.imageReference,
                    contentDescription = product.name,
                    modifier = Modifier.fillMaxSize()
                )
                Surface(
                    shape = RoundedCornerShape(topStart = 0.dp, bottomEnd = 8.dp),
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.align(Alignment.TopStart)
                ) {
                    Text(
                        text = "DEAL",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onError,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = product.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                product.brandName?.let {
                    Text(
                        text = it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "৳ ${product.displayPrice ?: product.price ?: "0.00"}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    if (!product.discountPrice.isNullOrBlank() && product.price != null && product.discountPrice != product.price) {
                        Text(
                            text = "৳ ${product.price}",
                            style = MaterialTheme.typography.bodySmall,
                            textDecoration = TextDecoration.LineThrough,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            IconButton(
                onClick = onAddToCart,
                modifier = Modifier
                    .size(48.dp)
                    .testTag("deal_add_cart_${product.id}")
            ) {
                Icon(
                    imageVector = Icons.Default.AddShoppingCart,
                    contentDescription = stringResource(R.string.add_to_cart),
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}
