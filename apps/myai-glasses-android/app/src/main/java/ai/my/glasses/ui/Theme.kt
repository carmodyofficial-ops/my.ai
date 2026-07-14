package ai.my.glasses.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * my.ai brand theme for the glasses companion — mirrors the web app's design
 * tokens (static/style.css :root + static/myai_theme.css) so the two feel like
 * one product: a dark One-Dark surface, cyan body text, teal borders, a
 * light-grey brand accent, and blue highlights.
 */
private object MyAi {
    val Bg = Color(0xFF282C34)            // --bg
    val Surface = Color(0xFF20242B)       // cards, a touch darker than bg
    val SurfaceHi = Color(0xFF2B3038)     // elevated / pressed
    val Fg = Color(0xFF9CDEF2)            // --fg (cyan body text)
    val FgMuted = Color(0xFFA9C2CC)       // secondary text
    val Border = Color(0xFF355A66)        // --border (teal)
    val BorderDim = Color(0xFF294049)
    val BrandGrey = Color(0xFFE5E7EB)     // --myai-accent-strong (brand/primary)
    val AccentBlue = Color(0xFF00AAFF)    // --color-accent
    val Green = Color(0xFF50FA7B)         // --green (connected/ok)
    val Red = Color(0xFFE06C75)           // --red (errors)
    val Ink = Color(0xFF14171C)           // text on light surfaces
}

private val MyAiColorScheme = darkColorScheme(
    primary = MyAi.BrandGrey,
    onPrimary = MyAi.Ink,
    primaryContainer = MyAi.SurfaceHi,
    onPrimaryContainer = MyAi.BrandGrey,
    secondary = MyAi.AccentBlue,
    onSecondary = MyAi.Ink,
    secondaryContainer = Color(0xFF12303F),
    onSecondaryContainer = MyAi.Fg,
    tertiary = MyAi.Green,
    onTertiary = Color(0xFF06210F),
    background = MyAi.Bg,
    onBackground = MyAi.Fg,
    surface = MyAi.Surface,
    onSurface = MyAi.Fg,
    surfaceVariant = MyAi.SurfaceHi,
    onSurfaceVariant = MyAi.FgMuted,
    // Card/sheet/menu backgrounds paint from the surfaceContainer roles — if we
    // leave them at Material's baseline they carry a purple tint. Pin them to
    // the my.ai neutral greys so cards read grey, not violet. surfaceTint is set
    // to the surface itself so elevation overlays don't reintroduce a tint.
    surfaceContainerLowest = MyAi.Bg,
    surfaceContainerLow = Color(0xFF1C2026),
    surfaceContainer = MyAi.Surface,
    surfaceContainerHigh = MyAi.SurfaceHi,
    surfaceContainerHighest = Color(0xFF313742),
    surfaceTint = MyAi.Surface,
    inverseSurface = MyAi.Fg,
    inverseOnSurface = MyAi.Bg,
    outline = MyAi.Border,
    outlineVariant = MyAi.BorderDim,
    error = MyAi.Red,
    onError = Color(0xFF1A0E10),
    errorContainer = Color(0xFF3A2023),
    onErrorContainer = Color(0xFFF3B4B9),
    scrim = Color(0xCC05070A),
)

/** Brand grey for the wordmark / headings, exposed for direct use. */
val MyAiBrand = MyAi.BrandGrey
val MyAiAccent = MyAi.AccentBlue
val MyAiConnected = MyAi.Green

private val MyAiTypography = Typography().let { base ->
    base.copy(
        headlineMedium = base.headlineMedium.copy(
            fontWeight = FontWeight.SemiBold, letterSpacing = (-0.5).sp),
        titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
        displaySmall = base.displaySmall.copy(
            fontWeight = FontWeight.Bold, letterSpacing = 4.sp),
    )
}

@Composable
fun MyAiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = MyAiColorScheme,
        typography = MyAiTypography,
        content = content,
    )
}
