package com.nexhaat.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.CategoryDto

@Composable
fun CategoryCard(
    category: CategoryDto,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    fillWidth: Boolean = false
) {
    Card(
        modifier = modifier
            .then(if (fillWidth) Modifier.fillMaxWidth() else Modifier.width(152.dp))
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
            ProductImage(
                imageUrl = category.imageReference,
                contentDescription = category.name,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(96.dp)
            )
            Column(
                modifier = Modifier
                    .padding(horizontal = 12.dp)
                    .padding(vertical = 8.dp)
            ) {
                Text(
                    category.name,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    stringResource(R.string.shop_now),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}
