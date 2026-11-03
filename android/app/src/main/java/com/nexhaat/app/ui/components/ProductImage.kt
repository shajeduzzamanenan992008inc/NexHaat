package com.nexhaat.app.ui.components

import android.util.Log
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImagePainter
import coil.compose.rememberAsyncImagePainter
import com.nexhaat.app.BuildConfig
import com.nexhaat.app.R
import com.nexhaat.app.data.remote.ImageUrlResolver
import com.nexhaat.app.data.remote.MediaBaseUrlResolver

@Composable
fun ProductImage(
    imageUrl: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    contentScale: ContentScale = ContentScale.Crop,
    fallbackHint: String? = null
) {
    val resolvedImageUrl = remember(imageUrl, BuildConfig.MEDIA_BASE_URL, BuildConfig.MEDIA_BASE_URL_RUNTIME_FALLBACK) {
        val direct = ImageUrlResolver.resolve(
            imageUrl,
            MediaBaseUrlResolver.resolvedOrFallbackString(
                resolvedFlag = BuildConfig.MEDIA_BASE_URL_RESOLVED,
                buildTimeValue = BuildConfig.MEDIA_BASE_URL,
                runtimeFallback = BuildConfig.MEDIA_BASE_URL_RUNTIME_FALLBACK
            )
        ) ?: ImageUrlResolver.resolveFromBackendAbsolute(imageUrl)
        direct ?: ImageUrlResolver.getCategoryFallback(fallbackHint ?: contentDescription)
    }

    val painter = rememberAsyncImagePainter(
        model = resolvedImageUrl ?: ImageUrlResolver.getCategoryFallback(fallbackHint ?: contentDescription)
    )
    val painterState = painter.state
    LaunchedEffect(painterState, resolvedImageUrl) {
        if (BuildConfig.DEBUG && painterState is AsyncImagePainter.State.Error) {
            Log.w("NexHaatImage", "Product image failed to load or decode: $resolvedImageUrl")
        }
    }

    when (painterState) {
        is AsyncImagePainter.State.Success -> Image(
            painter = painter,
            contentDescription = contentDescription,
            modifier = modifier,
            contentScale = contentScale
        )
        is AsyncImagePainter.State.Loading,
        AsyncImagePainter.State.Empty -> Box(
            modifier = modifier
                .background(MaterialTheme.colorScheme.surfaceVariant)
                .semantics { this.contentDescription = contentDescription.orEmpty() },
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator(strokeWidth = 2.dp)
        }
        is AsyncImagePainter.State.Error -> {
            // Secondary fallback image painter
            val secondaryModel = remember(fallbackHint, contentDescription) {
                ImageUrlResolver.getCategoryFallback(fallbackHint ?: contentDescription)
            }
            val fallbackPainter = rememberAsyncImagePainter(model = secondaryModel)
            if (fallbackPainter.state is AsyncImagePainter.State.Success) {
                Image(
                    painter = fallbackPainter,
                    contentDescription = contentDescription,
                    modifier = modifier,
                    contentScale = contentScale
                )
            } else {
                ProductImageFallback(modifier, contentDescription)
            }
        }
    }
}

@Composable
private fun ProductImageFallback(modifier: Modifier, imageDescription: String?) {
    val fallbackDescription = stringResource(R.string.no_image)
    Box(
        modifier = modifier
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .semantics {
                contentDescription = listOfNotNull(imageDescription, fallbackDescription)
                    .distinct()
                    .joinToString(", ")
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = stringResource(R.string.no_image),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodySmall
        )
    }
}
