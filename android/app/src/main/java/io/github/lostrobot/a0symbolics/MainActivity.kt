package io.github.lostrobot.a0symbolics

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private const val PREFS = "a0_android"
private const val KEY_URL = "server_url"

private val AgentZeroDarkColors = darkColorScheme(
    primary = Color(0xFF9B87F5),
    onPrimary = Color(0xFF100A22),
    primaryContainer = Color(0xFF2B2150),
    onPrimaryContainer = Color(0xFFE7DEFF),
    secondary = Color(0xFF79D7FF),
    background = Color(0xFF090A0D),
    onBackground = Color(0xFFF4F2F7),
    surface = Color(0xFF121318),
    onSurface = Color(0xFFF4F2F7),
    surfaceVariant = Color(0xFF1B1C23),
    onSurfaceVariant = Color(0xFFB9B7C2),
    outline = Color(0xFF77737F),
    outlineVariant = Color(0xFF34323B),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme(colorScheme = AgentZeroDarkColors) {
                AgentZeroApp()
            }
        }
    }
}

@Composable
private fun AgentZeroApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE) }
    var server by remember { mutableStateOf(prefs.getString(KEY_URL, null)) }
    if (server == null) {
        SetupScreen { url ->
            prefs.edit().putString(KEY_URL, url).apply()
            server = url
        }
    } else {
        SessionScreen(server!!) {
            prefs.edit().remove(KEY_URL).apply()
            server = null
        }
    }
}
