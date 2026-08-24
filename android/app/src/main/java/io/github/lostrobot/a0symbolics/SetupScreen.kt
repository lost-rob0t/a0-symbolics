package io.github.lostrobot.a0symbolics

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.net.URI

internal fun normalizeUrl(raw: String): Result<String> = runCatching {
    val u = URI(raw.trim())
    require(u.scheme == "http" || u.scheme == "https") { "Use http:// or https://" }
    require(!u.host.isNullOrBlank()) { "Enter a valid host or IP" }
    require(u.userInfo == null) { "Do not put credentials in the URL" }
    URI(
        u.scheme.lowercase(),
        null,
        u.host.lowercase(),
        u.port,
        u.path?.trimEnd('/')?.ifBlank { null },
        null,
        null,
    ).toString().trimEnd('/')
}

internal fun origin(url: String): String? = runCatching {
    val u = URI(url)
    "${u.scheme.lowercase()}://${u.host.lowercase()}${if (u.port >= 0) ":${u.port}" else ""}"
}.getOrNull()

private fun isLoopback(raw: String): Boolean = runCatching {
    val host = URI(raw.trim()).host?.lowercase() ?: return@runCatching false
    host == "localhost" || host == "::1" || host.startsWith("127.")
}.getOrDefault(false)

@Composable
internal fun SetupScreen(onConnect: (String) -> Unit) {
    var raw by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    val loopback = remember(raw) { isLoopback(raw) }
    val background = Brush.verticalGradient(
        listOf(
            Color(0xFF121018),
            MaterialTheme.colorScheme.background,
            Color(0xFF07080B),
        ),
    )

    Box(
        Modifier
            .fillMaxSize()
            .background(background)
            .statusBarsPadding()
            .navigationBarsPadding(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 22.dp, vertical = 22.dp),
            verticalArrangement = Arrangement.spacedBy(22.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Surface(
                    modifier = Modifier.size(56.dp),
                    shape = RoundedCornerShape(17.dp),
                    color = MaterialTheme.colorScheme.primary,
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            "A0",
                            color = MaterialTheme.colorScheme.onPrimary,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Black,
                        )
                    }
                }
                Column {
                    Text(
                        "Agent Zero",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "Android client",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text(
                    "Connect to your instance",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    "The app opens the real Agent Zero WebUI, so plugins, sessions and WebSockets keep working normally.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Surface(
                shape = RoundedCornerShape(22.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 2.dp,
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    Text(
                        "Server",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )

                    OutlinedTextField(
                        value = raw,
                        onValueChange = {
                            raw = it
                            error = null
                        },
                        label = { Text("Agent Zero URL") },
                        placeholder = { Text("http://192.168.1.50:5080") },
                        supportingText = error?.let { msg -> { Text(msg) } },
                        isError = error != null,
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )

                    if (loopback) {
                        Surface(
                            shape = RoundedCornerShape(14.dp),
                            color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.72f),
                        ) {
                            Column(
                                modifier = Modifier.padding(14.dp),
                                verticalArrangement = Arrangement.spacedBy(4.dp),
                            ) {
                                Text(
                                    "127.0.0.1 is this phone",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onTertiaryContainer,
                                )
                                Text(
                                    "If Agent Zero runs on another computer, use that computer's LAN IP instead, such as http://192.168.1.50:5080. Loopback only works when Agent Zero is running on this Android device or when using adb reverse.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onTertiaryContainer,
                                )
                            }
                        }
                    }

                    Button(
                        onClick = {
                            normalizeUrl(raw)
                                .onSuccess(onConnect)
                                .onFailure { error = it.message ?: "Invalid URL" }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(54.dp),
                        shape = RoundedCornerShape(15.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary,
                        ),
                    ) {
                        Text("Connect", fontWeight = FontWeight.Bold)
                    }
                }
            }

            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
                Text(
                    "LAN HTTP is supported. Your Agent Zero server must listen on its LAN interface (for example 0.0.0.0), not only desktop-side 127.0.0.1.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "For remote access, HTTPS is recommended.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(Modifier.height(6.dp))
        }
    }
}
