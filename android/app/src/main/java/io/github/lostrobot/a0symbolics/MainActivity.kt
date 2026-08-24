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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF8FF0C8),
                    secondary = Color(0xFF8BD7F8),
                    background = Color(0xFF080C0E),
                    surface = Color(0xFF101619),
                ),
            ) { AgentZeroApp() }
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
