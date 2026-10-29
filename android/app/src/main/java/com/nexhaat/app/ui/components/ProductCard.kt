package com.nexhaat.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.width
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.ProductDto
import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

@Composable
fun ProductCard(
    product: ProductDto,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val title = product.localizedName?.takeIf(String::isNotBlank) ?: product.name
    val price = product.displayPrice ?: product.discountPrice ?: product.price
    val previousPrice = product.discountPrice?.let { product.price }
    val currentPriceNumber = price?.toBigDecimalOrNull()
    val previousPriceNumber = previousPrice?.toBigDecimalOrNull()
    val discount = if (currentPriceNumber != null && previousPriceNumber != null && previousPriceNumber > BigDecimal.ZERO) {
        ((previousPriceNumber - currentPriceNumber) * BigDecimal(100) / previousPriceNumber)
            .toInt()
            .coerceIn(0, 100)
    } else {
        0
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column {
            androidx.compose.foundation.layout.Box {
                ProductImage(
                    imageUrl = product.image,
                    contentDescription = title,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(152.dp)
                )
                if (discount > 0) {
                    Text(
                        text = stringResource(R.string.discount_percent, discount),
                        color = MaterialTheme.colorScheme.onError,
                        style = MaterialTheme.typography.labelMedium,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(9.dp)
                            .background(MaterialTheme.colorScheme.error, RoundedCornerShape(999.dp))
                            .padding(horizontal = 9.dp, vertical = 5.dp)
                    )
                }
            }
            Column(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 11.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                product.brandName?.takeIf(String::isNotBlank)?.let { brand ->
                    Text(
                        text = brand,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 2,
                    minLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    price?.let { amount ->
                        Text(
                            text = formatPrice(amount),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                    if (previousPrice != null) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = formatPrice(previousPrice),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1
                        )
                    }
                }
                if ((product.stock ?: 0) > 0) {
                    Text(
                        text = stringResource(R.string.inventory_count, product.stock ?: 0),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
        }
    }
}

private fun formatPrice(value: String): String {
    val amount = value.toBigDecimalOrNull() ?: return value
    val formatted = NumberFormat.getNumberInstance(Locale("en", "BD")).apply {
        minimumFractionDigits = 2
        maximumFractionDigits = 2
    }.format(amount)
    return "৳$formatted"
}
