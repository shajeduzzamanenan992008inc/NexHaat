package com.nexhaat.app.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.nexhaat.app.R

@Composable
fun MarketplaceTopBar(
    onSearch: (() -> Unit)? = null,
    onNavigateBack: (() -> Unit)? = null,
    onCart: (() -> Unit)? = null,
    onSettings: (() -> Unit)? = null,
    onWishlist: (() -> Unit)? = null,
    onNotifications: (() -> Unit)? = null
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 2.dp,
        shadowElevation = 3.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(
                    WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal)
                )
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            onNavigateBack?.let { navigateBack ->
                IconButton(onClick = navigateBack, modifier = Modifier.testTag("topbar_back")) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.back))
                }
            }
            Image(
                painter = painterResource(R.drawable.logo),
                contentDescription = stringResource(R.string.app_name),
                modifier = Modifier.size(36.dp)
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.app_name),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.ExtraBold,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = stringResource(R.string.marketplace_tagline),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            onSearch?.let { search ->
                IconButton(onClick = search, modifier = Modifier.size(40.dp).testTag("topbar_search")) {
                    Icon(Icons.Default.Search, contentDescription = stringResource(R.string.search))
                }
            }
            onWishlist?.let { wishlist ->
                IconButton(onClick = wishlist, modifier = Modifier.size(40.dp).testTag("topbar_wishlist")) {
                    Icon(Icons.Default.FavoriteBorder, contentDescription = stringResource(R.string.wishlist))
                }
            }
            onNotifications?.let { notifications ->
                IconButton(onClick = notifications, modifier = Modifier.size(40.dp).testTag("topbar_notifications")) {
                    Icon(Icons.Default.Notifications, contentDescription = stringResource(R.string.notifications))
                }
            }
            onCart?.let { cart ->
                IconButton(onClick = cart, modifier = Modifier.size(40.dp).testTag("topbar_cart")) {
                    Icon(Icons.Default.ShoppingCart, contentDescription = stringResource(R.string.cart))
                }
            }
            onSettings?.let { settings ->
                IconButton(onClick = settings, modifier = Modifier.size(40.dp).testTag("topbar_settings")) {
                    Icon(Icons.Default.Security, contentDescription = stringResource(R.string.security_settings))
                }
            }
        }
    }
}
