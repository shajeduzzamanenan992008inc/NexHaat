package com.nexhaat.app.ui.theme

import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing

/**
 * NexHaat Unified Motion Tokens for Android Jetpack Compose
 *
 * Matched to the NexHaat Web motion system while respecting native Android animation scale:
 * - Durations: Instant (100ms), Fast (150ms), Normal (280ms), Page (320ms), Major (450ms)
 * - Easings: Spring, Decelerate, Accelerate, Standard
 */
object MotionTokens {
    const val DurationInstant = 100
    const val DurationFast = 150
    const val DurationNormal = 280
    const val DurationPage = 320
    const val DurationMajor = 450
    const val DurationDeliberate = DurationMajor
    const val DurationComplex = DurationMajor

    // Easing curves matching Web CSS cubic-bezier definitions
    val EasingSpring: Easing = CubicBezierEasing(0.175f, 0.885f, 0.32f, 1.275f)
    val EasingDecelerate: Easing = LinearOutSlowInEasing
    val EasingAccelerate: Easing = CubicBezierEasing(0.4f, 0.0f, 1.0f, 1.0f)
    val EasingStandard: Easing = FastOutSlowInEasing
}
