package com.nexhaat.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = NexHaatBlueLight,
    onPrimary = NexHaatDarkBackground,
    primaryContainer = Color(0xFF123D72),
    onPrimaryContainer = Color(0xFFEAF2FF),
    secondary = NexHaatAmberLight,
    onSecondary = NexHaatBlueDeep,
    secondaryContainer = Color(0xFF4A2B09),
    onSecondaryContainer = Color(0xFFFFE5BE),
    tertiary = NexHaatBlueLight,
    background = NexHaatDarkBackground,
    onBackground = NexHaatDarkInk,
    surface = NexHaatDarkSurface,
    onSurface = NexHaatDarkInk,
    surfaceVariant = NexHaatDarkRaised,
    onSurfaceVariant = NexHaatDarkMuted,
    outline = Color(0xFF3A5272),
    error = Color(0xFFFF756E)
)

private val LightColorScheme = lightColorScheme(
    primary = NexHaatBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFEAF2FF),
    onPrimaryContainer = NexHaatBlueDeep,
    secondary = NexHaatBlueDeep,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFEAF2FF),
    onSecondaryContainer = NexHaatBlueDeep,
    tertiary = NexHaatOrange,
    onTertiary = Color(0xFF2C2108),
    tertiaryContainer = Color(0xFFFFF2D9),
    onTertiaryContainer = Color(0xFF573B08),
    background = NexHaatPage,
    onBackground = NexHaatInk,
    surface = NexHaatSurface,
    onSurface = NexHaatInk,
    surfaceVariant = NexHaatSurfaceRaised,
    onSurfaceVariant = NexHaatMuted,
    outline = NexHaatLine,
    error = NexHaatRed
)

@Composable
fun NexHaatTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            window.navigationBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !darkTheme
                isAppearanceLightNavigationBars = !darkTheme
            }
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = NexHaatTypography,
        content = content
    )
}
