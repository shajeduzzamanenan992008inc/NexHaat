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
    primaryContainer = NexHaatBlueDeep,
    onPrimaryContainer = NexHaatDarkInk,
    secondary = Color(0xFF7BCF9A),
    onSecondary = NexHaatDarkBackground,
    tertiary = Color(0xFFF0B74F),
    background = NexHaatDarkBackground,
    onBackground = NexHaatDarkInk,
    surface = NexHaatDarkSurface,
    onSurface = NexHaatDarkInk,
    surfaceVariant = NexHaatDarkRaised,
    onSurfaceVariant = NexHaatDarkMuted,
    outline = Color(0xFF435365),
    error = Color(0xFFFFB4AB)
)

private val LightColorScheme = lightColorScheme(
    primary = NexHaatBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD8E9FA),
    onPrimaryContainer = NexHaatBlueDeep,
    secondary = NexHaatGreen,
    onSecondary = Color.White,
    tertiary = NexHaatOrange,
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
