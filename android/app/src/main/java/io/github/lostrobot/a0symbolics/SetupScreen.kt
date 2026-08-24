package io.github.lostrobot.a0symbolics

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
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
    URI(u.scheme.lowercase(), null, u.host.lowercase(), u.port, u.path?.trimEnd('/')?.ifBlank { null }, null, null)
        .toString().trimEnd('/')
}

internal fun origin(url: String): String? = runCatching {
    val u = URI(url)
    "${u.scheme.lowercase()}://${u.host.lowercase()}${if (u.port >= 0) ":${u.port}" else ""}"
}.getOrNull()

@Composable
internal fun SetupScreen(onConnect: (String) -> Unit) {
    var raw by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    val bg = Brush.verticalGradient(listOf(MaterialTheme.colorScheme.primary.copy(alpha = .18f), MaterialTheme.colorScheme.background))
    Box(Modifier.fillMaxSize().background(bg).statusBarsPadding().navigationBarsPadding()) {
        Column(Modifier.fillMaxWidth().align(Alignment.Center).padding(24.dp)) {
            Surface(shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.primaryContainer) {
                Text("A0", Modifier.padding(horizontal = 18.dp, vertical = 14.dp), fontWeight = FontWeight.Black, style = MaterialTheme.typography.headlineMedium)
            }
            Spacer(Modifier.height(22.dp))
            Text("Agent Zero", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Black)
            Text(
                "Full Agent Zero WebUI on Android. Plugins, WebSockets and server auth stay native to Agent Zero.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
            )
            Card(shape = RoundedCornerShape(28.dp)) {
                Column(Modifier.padding(20.dp)) {
                    Text("Connect to an instance", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    OutlinedTextField(
                        value = raw,
                        onValueChange = { raw = it; error = null },
                        label = { Text("Agent Zero URL") },
                        placeholder = { Text("http://192.168.1.50:50001") },
                        supportingText = error?.let { msg -> { Text(msg) } },
                        isError = error != null,
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    )
                    Button(
                        onClick = { normalizeUrl(raw).onSuccess(onConnect).onFailure { error = it.message ?: "Invalid URL" } },
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    ) { Text("Open Agent Zero") }
                    Text(
                        "HTTP is supported for LAN instances but is not encrypted.",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 10.dp),
                    )
                }
            }
        }
    }
}
