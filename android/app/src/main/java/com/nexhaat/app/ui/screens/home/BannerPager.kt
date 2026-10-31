package com.nexhaat.app.ui.screens.home

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.util.lerp
import androidx.compose.ui.zIndex
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.dto.BannerDto
import com.nexhaat.app.ui.components.ProductImage
import com.nexhaat.app.ui.theme.NexHaatBlue
import com.nexhaat.app.ui.theme.NexHaatBlueDeep
import kotlinx.coroutines.delay
import kotlin.math.absoluteValue

/** Duration the carousel pauses after a user touch before resuming auto-slide. */
private const val AUTO_SLIDE_INTERVAL_MS = 5000L
private const val AUTO_SLIDE_PAUSE_MS = 3000L

/**
 * Swipeable banner carousel with automatic sliding.
 *
 * When [banners] is empty the carousel shows a branded discovery card instead of
 * inventing promotions.
 *
 * Supports light and dark themes through MaterialTheme color scheme. Banner images
 * are loaded through [ProductImage], which uses Coil and the existing media URL
 * resolver with a branded fallback. The entire card is tappable for navigation.
 */
@Composable
fun NexHaatBannerCarousel(
    banners: List<BannerDto>,
    modifier: Modifier = Modifier,
    onBannerClick: (BannerDto) -> Unit = {},
    enabled: Boolean = true
) {
    if (banners.isEmpty()) {
        NexHaatBannerPlaceholder(modifier = modifier)
        return
    }

    val pagerState = rememberPagerState(pageCount = { banners.size })
    var isPaused by remember { mutableStateOf(false) }
    var lastInteractionTime by remember { mutableLongStateOf(0L) }

    // Auto-slide loop: pauses after interaction, resumes after the pause window.
    LaunchedEffect(pagerState.currentPage) {
        while (true) {
            delay(AUTO_SLIDE_INTERVAL_MS)
            val elapsed = System.currentTimeMillis() - lastInteractionTime
            if (!isPaused && elapsed > AUTO_SLIDE_PAUSE_MS && enabled && banners.size > 1) {
                val next = (pagerState.currentPage + 1) % banners.size
 pagerState.animateScrollToPage(next)
            }
        }
    }

    val pageLabel = stringResource(
        R.string.banner_page_of,
        pagerState.currentPage + 1,
        banners.size
    )

    Column(modifier = modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(3f / 1f)
                .clip(RoundedCornerShape(24.dp))
                .semantics {
                    contentDescription = pageLabel
                }
                .zIndex(1f)
                .pointerInput(Unit) {
                    detectTapGestures(onTap = {
                        isPaused = true
                        lastInteractionTime = System.currentTimeMillis()
                    })
                }
        ) {
            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize()
            ) { page ->
                val pageOffset = (
                    (pagerState.currentPage - page) + pagerState.currentPageOffsetFraction
                    ).absoluteValue.coerceIn(0f, 1f)
                BannerPage(
                    banner = banners[page],
                    modifier = Modifier
                        .fillMaxSize()
                        .graphicsLayer {
                            alpha = lerp(0.82f, 1f, 1f - pageOffset)
                            val scale = lerp(0.96f, 1f, 1f - pageOffset)
                            scaleX = scale
                            scaleY = scale
                        },
                    onClick = { onBannerClick(banners[page]) },
                    pageIndex = page,
                    totalPages = banners.size
                )
            }
        }

        // Page indicators
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 10.dp)
                .semantics {
                    contentDescription = "Displaying banner ${pagerState.currentPage + 1} of ${banners.size}"
                },
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            banners.forEachIndexed { index, _ ->
                val isActive = pagerState.currentPage == index
                val width by animateDpAsState(
                    targetValue = if (isActive) 24.dp else 8.dp,
                    label = "banner-indicator-width"
                )
                val color by animateColorAsState(
                    targetValue = if (isActive) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurface.copy(alpha = 0.22f)
                    },
                    label = "banner-indicator-color"
                )
                Box(
                    modifier = Modifier
                        .padding(horizontal = 4.dp)
                        .width(width)
                        .height(8.dp)
                        .clip(CircleShape)
                        .background(color)
                )
            }
        }
    }
}

@Composable
private fun BannerPage(
    banner: BannerDto,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    pageIndex: Int,
    totalPages: Int
) {
    val title = banner.title.ifBlank { stringResource(R.string.discover_nexhaat) }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(24.dp))
            .background(
                Brush.horizontalGradient(listOf(NexHaatBlue, NexHaatBlueDeep))
            )
            .semantics {
                contentDescription = "$title, banner ${pageIndex + 1} of $totalPages"
            }
            .pointerInput(Unit) {
                detectTapGestures(onTap = { onClick() })
            }
    ) {
        // Banner image (loaded via Coil with existing resolver + branded fallback)
        if (!banner.imageUrl.isNullOrBlank()) {
            ProductImage(
                imageUrl = banner.imageUrl,
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        }

        // Dark gradient overlay for text readability
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.55f))
                    )
                )
        )

        // Text content with proper contrast
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomStart)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            if (!banner.subtitle.isNullOrBlank()) {
                Text(
                    text = banner.subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.9f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
private fun NexHaatBannerPlaceholder(
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(3f / 1f)
            .clip(RoundedCornerShape(24.dp))
            .background(
                Brush.horizontalGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.07f),
                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.05f)
                    )
                )
            )
            .padding(22.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(
                    Brush.horizontalGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary,
                            MaterialTheme.colorScheme.primaryContainer
                        )
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = stringResource(R.string.banner_placeholder_icon),
                style = MaterialTheme.typography.titleLarge,
                color = Color.White
            )
        }
        Spacer(modifier = Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.discover_nexhaat),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(modifier = Modifier.height(3.dp))
        Text(
            text = stringResource(R.string.explore_products_and_categories),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}
