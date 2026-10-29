package com.nexhaat.app.ui.screens.product

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.data.remote.dto.VariantDto
import com.nexhaat.app.ui.components.ErrorState
import com.nexhaat.app.ui.components.MarketplaceBottomBar
import com.nexhaat.app.ui.components.MarketplaceTab
import com.nexhaat.app.ui.components.MarketplaceTopBar
import com.nexhaat.app.ui.components.ProductImage
import java.text.NumberFormat
import java.util.Locale

@Composable
fun ProductDetailScreen(
    viewModel: ProductDetailViewModel = hiltViewModel(),
    productId: Int,
    onNavigateBack: () -> Unit,
    onNavigateToHome: () -> Unit = {},
    onNavigateToCategories: () -> Unit = {},
    onNavigateToSearch: () -> Unit = {},
    onNavigateToCart: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(productId) {
        viewModel.loadProduct(productId)
    }

    Scaffold(
        topBar = {
            MarketplaceTopBar(
                onSearch = onNavigateToSearch,
                onNavigateBack = onNavigateBack,
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
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        when {
            uiState.isLoading && uiState.product == null -> androidx.compose.foundation.layout.Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentAlignment = Alignment.Center
            ) { CircularProgressIndicator() }
            uiState.error != null && uiState.product == null -> ErrorState(
                message = uiState.error ?: stringResource(R.string.error_occurred),
                onRetry = { viewModel.loadProduct(productId) },
                modifier = Modifier.padding(paddingValues)
            )
            uiState.product != null -> {
                val product = uiState.product!!
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .verticalScroll(rememberScrollState())
                ) {
                    ProductImage(
                        imageUrl = product.image,
                        contentDescription = product.localizedName ?: product.name,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(310.dp),
                        contentScale = ContentScale.Crop
                    )
                    Column(
                        modifier = Modifier.padding(18.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        ProductDetailContent(
                            product = product,
                            uiState = uiState,
                            onSelectVariant = viewModel::selectVariant,
                            onAddToCart = viewModel::addToCart,
                            onOpenCart = onNavigateToCart
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ProductDetailContent(
    product: ProductDto,
    uiState: ProductDetailUiState,
    onSelectVariant: (Int) -> Unit,
    onAddToCart: () -> Unit,
    onOpenCart: () -> Unit
) {
    val title = product.localizedName?.takeIf(String::isNotBlank) ?: product.name
    val description = product.localizedDescription?.takeIf(String::isNotBlank) ?: product.description
    val price = product.displayPrice ?: product.discountPrice ?: product.price
    val stock = product.stock ?: 0
    val variants = product.variants
    val selectedVariant = variants.firstOrNull { it.id == uiState.selectedVariantId }

    product.brandName?.takeIf(String::isNotBlank)?.let {
        Text(it, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
    }
    Text(title, style = MaterialTheme.typography.headlineSmall)
    price?.let {
        Text(
            formatDetailPrice(it),
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
    }
    if (product.discountPrice != null && product.price != null) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = stringResource(R.string.regular_price, formatDetailPrice(product.price)),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = product.discountPrice.let(::formatDetailPrice),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Text(
            text = if (stock > 0) stringResource(R.string.inventory_count, stock)
            else stringResource(R.string.out_of_stock),
            style = MaterialTheme.typography.bodyMedium,
            color = if (stock > 0) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)
        )
    }
    description?.takeIf(String::isNotBlank)?.let {
        Spacer(modifier = Modifier.height(4.dp))
        Text(stringResource(R.string.product_description), style = MaterialTheme.typography.titleMedium)
        Text(it, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    if (variants.isNotEmpty()) {
        Text(stringResource(R.string.product_options), style = MaterialTheme.typography.titleMedium)
        variants.forEach { variant ->
            VariantRow(
                variant = variant,
                selected = variant.id == uiState.selectedVariantId,
                onClick = { onSelectVariant(variant.id) }
            )
        }
    }
    val availableStock = selectedVariant?.stock ?: stock
    Button(
        onClick = onAddToCart,
        modifier = Modifier.fillMaxWidth(),
        enabled = availableStock > 0 && !uiState.isAddingToCart &&
            (variants.isEmpty() || uiState.selectedVariantId != null)
    ) {
        if (uiState.isAddingToCart) CircularProgressIndicator()
        else Text(stringResource(if (variants.isNotEmpty()) R.string.choose_options else R.string.add_to_cart))
    }
    uiState.cartMessage?.let { message ->
        Text(
            text = message,
            style = MaterialTheme.typography.bodySmall,
            color = if (uiState.requiresSignIn) MaterialTheme.colorScheme.error
            else MaterialTheme.colorScheme.secondary
        )
    }
    if (uiState.cartMessage == "Added to your cart.") {
        TextButton(onClick = onOpenCart) { Text(stringResource(R.string.view_cart)) }
    }
    if (uiState.requiresSignIn) {
        Text(
            stringResource(R.string.sign_in_to_cart),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun VariantRow(variant: VariantDto, selected: Boolean, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer
            else MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            RadioButton(selected = selected, onClick = onClick)
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    listOfNotNull(variant.optionName, variant.optionValue).joinToString(": "),
                    style = MaterialTheme.typography.titleSmall
                )
                Text(
                    if ((variant.stock ?: 0) > 0) stringResource(R.string.inventory_count, variant.stock ?: 0)
                    else stringResource(R.string.out_of_stock),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            variant.price?.let {
                Text(formatDetailPrice(it), style = MaterialTheme.typography.titleSmall)
            }
        }
    }
}

private fun formatDetailPrice(value: String): String {
    val amount = value.toBigDecimalOrNull() ?: return value
    val formatted = NumberFormat.getNumberInstance(Locale("en", "BD")).apply {
        minimumFractionDigits = 2
        maximumFractionDigits = 2
    }.format(amount)
    return "৳$formatted"
}
