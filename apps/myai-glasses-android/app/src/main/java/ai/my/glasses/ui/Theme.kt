package ai.my.glasses.ui

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * my.ai brand theme for the glasses companion.
 *
 * Dark, calm, and legible: a deep neutral ground with cards that sit ABOVE it
 * (lighter = elevated, the modern convention), light-neutral body text for
 * readability, and the my.ai cyan reserved as a brand ACCENT (the wordmark, active
 * voice, links) rather than painted over every line of text. Green = connected/ok,
 * red = errors. Rounded shapes + an intentional type scale carry the proportion.
 */
private object MyAi {
    val Bg = Color(0xFF1D2026)             // app ground (deepest)
    val Surface = Color(0xFF262A31)        // cards — LIGHTER than bg (elevation)
    val SurfaceHi = Color(0xFF2E333B)      // nested / pressed surfaces
    val SurfaceHigher = Color(0xFF373D46)
    val Fg = Color(0xFFE3E8EC)             // primary text (light neutral, readable)
    val FgMuted = Color(0xFF94A2AB)        // secondary / captions
    val Border = Color(0xFF333C44)         // hairline outlines (neutral)
    val BorderDim = Color(0xFF2A323A)
    val Brand = Color(0xFFF1F4F6)          // wordmark / primary filled buttons
    val Ink = Color(0xFF10141A)            // text on light/brand surfaces
    val Cyan = Color(0xFF74D4EE)           // brand accent (secondary)
    val CyanContainer = Color(0xFF123340)  // tonal accent surface
    val Green = Color(0xFF4ADE80)          // connected / ok
    val Red = Color(0xFFF07782)            // errors
}

private val MyAiColorScheme = darkColorScheme(
    primary = MyAi.Brand,
    onPrimary = MyAi.Ink,
    primaryContainer = MyAi.SurfaceHi,
    onPrimaryContainer = MyAi.Fg,
    secondary = MyAi.Cyan,
    onSecondary = MyAi.Ink,
    secondaryContainer = MyAi.CyanContainer,
    onSecondaryContainer = MyAi.Cyan,
    tertiary = MyAi.Green,
    onTertiary = Color(0xFF06210F),
    tertiaryContainer = Color(0xFF14351F),
    onTertiaryContainer = MyAi.Green,
    background = MyAi.Bg,
    onBackground = MyAi.Fg,
    surface = MyAi.Surface,
    onSurface = MyAi.Fg,
    surfaceVariant = MyAi.SurfaceHi,
    onSurfaceVariant = MyAi.FgMuted,
    // Pin every surfaceContainer role to the neutral ramp so cards/sheets/menus read
    // grey (Material's baseline tints them violet), and set surfaceTint to a surface
    // so elevation overlays don't reintroduce a tint.
    surfaceContainerLowest = MyAi.Bg,
    surfaceContainerLow = Color(0xFF22262C),
    surfaceContainer = MyAi.Surface,
    surfaceContainerHigh = MyAi.SurfaceHi,
    surfaceContainerHighest = MyAi.SurfaceHigher,
    surfaceTint = MyAi.Surface,
    inverseSurface = MyAi.Fg,
    inverseOnSurface = MyAi.Bg,
    outline = MyAi.Border,
    outlineVariant = MyAi.BorderDim,
    error = MyAi.Red,
    onError = Color(0xFF2A0E11),
    errorContainer = Color(0xFF3A2023),
    onErrorContainer = Color(0xFFF7C0C4),
    scrim = Color(0xCC05070A),
)

/** Brand tokens exposed for direct use where the scheme roles don't fit. */
val MyAiBrand = MyAi.Brand
val MyAiAccent = MyAi.Cyan
val MyAiConnected = MyAi.Green

// One UI runs markedly rounder than Material's baseline: cards and sheets read
// as soft rectangles, and the radius grows with the container. These are the
// proportions Samsung uses on phone-size surfaces.
private val MyAiShapes = Shapes(
    extraSmall = RoundedCornerShape(12.dp),
    small = RoundedCornerShape(16.dp),
    medium = RoundedCornerShape(22.dp),
    large = RoundedCornerShape(26.dp),
    extraLarge = RoundedCornerShape(32.dp),
)

private val MyAiTypography = Typography().let { b ->
    b.copy(
        displaySmall = b.displaySmall.copy(
            fontWeight = FontWeight.Bold, letterSpacing = 6.sp),
        // One UI screen titles are large and heavy — the expanded header is the
        // anchor of each screen, and it shrinks to headlineSmall when collapsed.
        headlineMedium = b.headlineMedium.copy(
            fontSize = 32.sp, lineHeight = 40.sp,
            fontWeight = FontWeight.Bold, letterSpacing = (-0.6).sp),
        headlineSmall = b.headlineSmall.copy(
            fontSize = 22.sp, lineHeight = 28.sp,
            fontWeight = FontWeight.Bold, letterSpacing = (-0.4).sp),
        titleLarge = b.titleLarge.copy(
            fontWeight = FontWeight.SemiBold, letterSpacing = (-0.2).sp),
        titleMedium = b.titleMedium.copy(fontWeight = FontWeight.SemiBold),
        bodyLarge = b.bodyLarge.copy(lineHeight = 22.sp),
        labelLarge = b.labelLarge.copy(fontWeight = FontWeight.SemiBold),
        labelMedium = b.labelMedium.copy(
            fontWeight = FontWeight.Medium, letterSpacing = 0.6.sp),
    )
}

@Composable
fun MyAiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = MyAiColorScheme,
        typography = MyAiTypography,
        shapes = MyAiShapes,
        content = content,
    )
}
