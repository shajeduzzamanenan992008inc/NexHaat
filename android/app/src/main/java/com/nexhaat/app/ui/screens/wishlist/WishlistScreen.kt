package com.nexhaat.app.ui.screens.wishlist

import android.widget.Toast
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
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductImage

@Composable
fun WishlistScreen(
    viewModel: WishlistViewModel = hiltViewModel(),
    onNavigateToProductDetail: (Int) -> Unit,
    onNavigateToHome: () -> Unit,
    onNavigateToCategories: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToCart: () -> Unit,
    onNavigateToSignIn: () -> Unit = {}
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
                onCart = onNavigateToCart
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
                is WishlistUiState.Loading -> LoadingState()
                is WishlistUiState.Error -> {
                    if (state.message.contains("Sign in", ignoreCase = true)) {
                        EmptyState(
                            title = stringResource(R.string.your_wishlist),
                            message = state.message,
                            buttonText = stringResource(R.string.sign_in),
                            onButtonClick = onNavigateToSignIn
                        )
                    } else {
                        ErrorState(
                            message = state.message,
                            onRetry = viewModel::loadWishlist
                        )
                    }
                }
                is WishlistUiState.Success -> {
                    if (state.products.isEmpty()) {
                        EmptyState(
                            title = stringResource(R.string.your_wishlist),
                            message = stringResource(R.string.wishlist_empty),
                            buttonText = stringResource(R.string.explore_marketplace),
                            onButtonClick = onNavigateToHome
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .testTag("wishlist_list"),
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(state.products, key = { it.id }) { product ->
                                WishlistItemCard(
                                    product = product,
                                    onClick = { onNavigateToProductDetail(product.id) },
                                    onMoveToCart = { viewModel.moveToCart(product) },
                                    onRemove = { viewModel.removeFromWishlist(product.id) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WishlistItemCard(
    product: ProductDto,
    onClick: () -> Unit,
    onMoveToCart: () -> Unit,
    onRemove: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag("wishlist_card_${product.id}"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(RoundedCornerShape(8.dp))
                ) {
                    ProductImage(
                        imageReference = product.imageReference,
                        contentDescription = product.name,
                        modifier = Modifier.fillMaxSize()
                    )
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
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "৳ ${product.displayPrice ?: product.price ?: "0.00"}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                IconButton(
                    onClick = onRemove,
                    modifier = Modifier
                        .size(48.dp)
                        .testTag("wishlist_remove_${product.id}")
                ) {
                    Icon(
                        imageVector = Icons.Default.Delete,
                        contentDescription = stringResource(R.string.remove),
                        tint = MaterialTheme.colorScheme.error
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Button(
                onClick = onMoveToCart,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .testTag("wishlist_move_cart_${product.id}"),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primaryContainer, contentColor = MaterialTheme.colorScheme.onPrimaryContainer)
            ) {
                Icon(Icons.Default.ShoppingCart, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = stringResource(R.string.move_to_cart), fontWeight = FontWeight.SemiBold)
            }
        }
    }
}
