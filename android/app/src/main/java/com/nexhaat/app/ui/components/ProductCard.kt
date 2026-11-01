package com.nexhaat.app.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ripple
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.nexhaat.app.data.remote.dto.ProductDto
import com.nexhaat.app.ui.components.ProductImage
import com.nexhaat.app.ui.theme.NexHaatColors
import com.nexhaat.app.ui.theme.NexHaatTypography

@Composable
fun ProductCard(
    product: ProductDto,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.98f else 1f,
        label = "scale"
    )

    val price = product.displayPrice?.toDoubleOrNull()
    val previous = product.price?.toDoubleOrNull()
    val showPrevious = previous != null &&
        price != null &&
        previous > 0 &&
        price < previous
    val discounted = showPrevious && product.isAvailable

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(NexHaatColors.surface())
            .clickable(
                interactionSource = interactionSource,
                indication = ripple(
                    bounded = true,
                    color = NexHaatColors.onSurface().copy(alpha = 0.18f)
                ),
                onClick = onClick
            )
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        // Product image
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(96.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(NexHaatColors.surfaceVariant())
        ) {
            ProductImage(
                imageUrl = product.imageReference,
                contentDescription = product.name.ifBlank { null },
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )

            if (discounted) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(6.dp)
                        .background(
                            NexHaatColors.error(),
                            RoundedCornerShape(4.dp)
                        )
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "SALE",
                        style = NexHaatTypography.labelSmall,
                        color = NexHaatColors.onError(),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        Text(
            text = product.brandName ?: "",
            style = NexHaatTypography.bodySmall,
            color = NexHaatColors.onSurfaceVariant()
        )

        Text(
            text = product.name.ifBlank { "Product name" },
            style = NexHaatTypography.bodyMedium,
            color = NexHaatColors.onSurface(),
            maxLines = 2,
            textAlign = TextAlign.Start,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(4.dp))

        Row(
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = product.displayPrice ?: "0.00",
                style = NexHaatTypography.bodyLarge,
                fontWeight = FontWeight.Bold,
                color = if (discounted) NexHaatColors.error() else NexHaatColors.onSurface()
            )

            if (showPrevious) {
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = String.format("%.2f", previous!!),
                    style = NexHaatTypography.bodySmall,
                    color = NexHaatColors.onSurfaceVariant(),
                    textDecoration = TextDecoration.LineThrough
                )
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = if (product.stock != null && product.stock > 0) "In stock" else "Out of stock",
            style = NexHaatTypography.bodySmall,
            color = if ((product.stock ?: 0) > 0) NexHaatColors.onSurface() else NexHaatColors.onSurfaceVariant()
        )
    }
}

