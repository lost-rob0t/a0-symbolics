package io.github.lostrobot.a0symbolics

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext

private const val PREFS = "a0_android"
private const val KEY_URL = "server_url"
private const val KEY_THEME_MODE = "theme_mode"
private const val KEY_DYNAMIC_COLOR = "dynamic_color"
internal const val DEFAULT_SERVER_URL = "http://127.0.0.1:5080"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { AgentZeroApp() }
    }
}

@Composable
private fun AgentZeroApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE) }
    var server by remember {
        mutableStateOf(prefs.getString(KEY_URL, null) ?: DEFAULT_SERVER_URL)
    }
    var editingServer by rememberSaveable { mutableStateOf(false) }
    var themeMode by remember {
        mutableStateOf(ThemeMode.fromStored(prefs.getString(KEY_THEME_MODE, null)))
    }
    var dynamicColor by remember {
        mutableStateOf(prefs.getBoolean(KEY_DYNAMIC_COLOR, false))
    }

    AgentZeroTheme(mode = themeMode, dynamicColor = dynamicColor) {
        if (editingServer) {
            SetupScreen(
                initialUrl = server,
                onConnect = { url ->
                    prefs.edit().putString(KEY_URL, url).apply()
                    server = url
                    editingServer = false
                },
                onCancel = { editingServer = false },
            )
        } else {
            SessionScreen(
                server = server,
                themeMode = themeMode,
                dynamicColor = dynamicColor,
                onChangeServer = { editingServer = true },
                onThemeModeChange = { mode ->
                    themeMode = mode
                    prefs.edit().putString(KEY_THEME_MODE, mode.name).apply()
                },
                onDynamicColorChange = { enabled ->
                    dynamicColor = enabled
                    prefs.edit().putBoolean(KEY_DYNAMIC_COLOR, enabled).apply()
                },
            )
        }
    }
}
