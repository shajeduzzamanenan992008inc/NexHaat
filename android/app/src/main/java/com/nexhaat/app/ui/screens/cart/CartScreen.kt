package com.nexhaat.app.ui.screens.cart

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.CartItemDto
import com.nexhaat.app.ui.components.EmptyState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import java.text.NumberFormat
import java.util.Locale

@Composable
fun CartScreen(
    viewModel: CartViewModel = hiltViewModel(),
    onNavigateToHome: () -> Unit,
    onNavigateToCategories: () -> Unit,
    onNavigateToSearch: () -> Unit,
    onNavigateToSignIn: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.loadCart() }

    Scaffold(
        topBar = { MarketplaceTopBar(onSearch = onNavigateToSearch) },
        bottomBar = {
            MarketplaceBottomBar(
                selectedTab = MarketplaceTab.Cart,
                onHome = onNavigateToHome,
                onCategories = onNavigateToCategories,
                onSearch = onNavigateToSearch,
                onCart = {}
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        when {
            uiState.isLoading && uiState.cart == null -> Column(
                modifier = Modifier.fillMaxSize().padding(padding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) { CircularProgressIndicator() }
            (uiState.error != null || uiState.hasUnexpectedResult) && uiState.cart == null -> Column(
                modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    uiState.error ?: stringResource(R.string.request_did_not_complete),
                    style = MaterialTheme.typography.bodyLarge
                )
                Spacer(Modifier.padding(8.dp))
                if (uiState.errorCode == "401" || uiState.errorCode == "403") {
                    Button(onClick = onNavigateToSignIn) { Text(stringResource(R.string.sign_in)) }
                }
                TextButton(onClick = viewModel::loadCart) { Text(stringResource(R.string.retry)) }
            }
            uiState.cart != null -> {
                val cart = uiState.cart!!
                if (cart.items.isEmpty()) {
                    EmptyState(
                        message = stringResource(R.string.empty_cart),
                        modifier = Modifier.fillMaxSize().padding(padding)
                    )
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize().padding(padding),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        item {
                            Text(
                                stringResource(R.string.your_cart),
                                style = MaterialTheme.typography.headlineSmall,
                                modifier = Modifier.padding(bottom = 4.dp)
                            )
                        }
                        items(cart.items, key = { it.key }) { item ->
                            CartLine(
                                item = item,
                                enabled = !uiState.isLoading,
                                onDecrease = { viewModel.updateQuantity(item.key, item.quantity - 1) },
                                onIncrease = { viewModel.updateQuantity(item.key, item.quantity + 1) },
                                onRemove = { viewModel.remove(item.key) }
                            )
                        }
                        item {
                            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                            TotalRow(stringResource(R.string.subtotal), cart.subtotal)
                            TotalRow(stringResource(R.string.delivery_fee), cart.deliveryFee)
                            TotalRow(stringResource(R.string.total), cart.total, emphasized = true)
                            Spacer(Modifier.padding(4.dp))
                            Text(
                                stringResource(R.string.checkout_not_available),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CartLine(
    item: CartItemDto,
    enabled: Boolean,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit,
    onRemove: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Text(item.name, style = MaterialTheme.typography.titleMedium)
        item.variantLabel?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
        Text(formatMoney(item.subtotal), fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.End
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // The symbol glyphs alone are not a useful screen-reader label, so each
                // 48dp control exposes an explicit localized description.
                val decreaseLabel = stringResource(R.string.decrease_quantity)
                val increaseLabel = stringResource(R.string.increase_quantity)
                IconButton(
                    onClick = onDecrease,
                    enabled = enabled,
                    modifier = Modifier.semantics { contentDescription = decreaseLabel }
                ) { Text("−") }
                Text(item.quantity.toString(), style = MaterialTheme.typography.titleMedium)
                IconButton(
                    onClick = onIncrease,
                    enabled = enabled && item.quantity < item.availableStock && item.quantity < 20,
                    modifier = Modifier.semantics { contentDescription = increaseLabel }
                ) { Text("+") }
                TextButton(onClick = onRemove, enabled = enabled) { Text(stringResource(R.string.remove)) }
            }
        }
    }
}

@Composable
private fun TotalRow(label: String, value: String, emphasized: Boolean = false) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, style = if (emphasized) MaterialTheme.typography.titleMedium else MaterialTheme.typography.bodyMedium)
        Text(
            formatMoney(value),
            style = if (emphasized) MaterialTheme.typography.titleLarge else MaterialTheme.typography.bodyMedium,
            fontWeight = if (emphasized) FontWeight.Bold else FontWeight.Normal
        )
    }
}

private fun formatMoney(value: String): String {
    val amount = value.toBigDecimalOrNull() ?: return value
    val localized = NumberFormat.getNumberInstance(Locale("en", "BD")).apply {
        minimumFractionDigits = 2
        maximumFractionDigits = 2
    }.format(amount)
    return "৳$localized"
}
