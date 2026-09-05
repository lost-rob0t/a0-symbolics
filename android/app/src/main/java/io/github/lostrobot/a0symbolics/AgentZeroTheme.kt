package io.github.lostrobot.a0symbolics

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

internal enum class ThemeMode {
    SYSTEM,
    DARK,
    LIGHT;

    companion object {
        fun fromStored(value: String?): ThemeMode = entries.firstOrNull { it.name == value } ?: SYSTEM
    }
}

private val AgentZeroDarkColors = darkColorScheme(
    primary = Color(0xFFB7A5FF),
    onPrimary = Color(0xFF241753),
    primaryContainer = Color(0xFF38296E),
    onPrimaryContainer = Color(0xFFE7DEFF),
    secondary = Color(0xFF82D7FF),
    background = Color(0xFF090A0D),
    onBackground = Color(0xFFF4F2F7),
    surface = Color(0xFF111217),
    onSurface = Color(0xFFF4F2F7),
    surfaceVariant = Color(0xFF1C1D23),
    onSurfaceVariant = Color(0xFFC7C4CE),
    outline = Color(0xFF918D99),
    outlineVariant = Color(0xFF393741),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
)

private val AgentZeroLightColors = lightColorScheme(
    primary = Color(0xFF5B45A6),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE7DEFF),
    onPrimaryContainer = Color(0xFF21114F),
    secondary = Color(0xFF00658A),
    background = Color(0xFFF9F7FC),
    onBackground = Color(0xFF1B1B1F),
    surface = Color(0xFFFFFBFF),
    onSurface = Color(0xFF1B1B1F),
    surfaceVariant = Color(0xFFE6E1EA),
    onSurfaceVariant = Color(0xFF48454E),
    outline = Color(0xFF79747E),
    outlineVariant = Color(0xFFCAC4D0),
    error = Color(0xFFBA1A1A),
    onError = Color.White,
)

@Composable
internal fun AgentZeroTheme(
    mode: ThemeMode,
    dynamicColor: Boolean,
    content: @Composable () -> Unit,
) {
    val systemDark = isSystemInDarkTheme()
    val dark = when (mode) {
        ThemeMode.SYSTEM -> systemDark
        ThemeMode.DARK -> true
        ThemeMode.LIGHT -> false
    }
    val context = LocalContext.current
    val colors = if (dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    } else {
        if (dark) AgentZeroDarkColors else AgentZeroLightColors
    }

    MaterialTheme(colorScheme = colors, content = content)
}
