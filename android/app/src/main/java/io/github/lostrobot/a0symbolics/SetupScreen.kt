package io.github.lostrobot.a0symbolics

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import java.net.URL

internal fun normalizeUrl(raw: String): Result<String> = runCatching {
    val text = raw.trim()
    require(text.isNotEmpty()) { "Enter an Agent Zero URL" }

    val url = URL(text)
    val scheme = url.protocol.lowercase()
    require(scheme == "http" || scheme == "https") { "Use http:// or https://" }
    require(url.userInfo == null) { "Do not put credentials in the URL" }

    val host = url.host.trim()
    require(host.isNotEmpty()) { "Enter a valid host or IP" }

    val normalizedHost = host
        .removePrefix("[")
        .removeSuffix("]")
        .lowercase()
        .let { if (it.contains(':')) "[$it]" else it }
    val port = if (url.port >= 0) ":${url.port}" else ""
    val path = url.path.trimEnd('/').let { if (it == "/") "" else it }

    "$scheme://$normalizedHost$port$path"
}

internal fun origin(url: String): String? = runCatching {
    val parsed = URL(url)
    val host = parsed.host
        .removePrefix("[")
        .removeSuffix("]")
        .lowercase()
        .let { if (it.contains(':')) "[$it]" else it }
    "${parsed.protocol.lowercase()}://$host${if (parsed.port >= 0) ":${parsed.port}" else ""}"
}.getOrNull()

private fun isLoopback(raw: String): Boolean = runCatching {
    val host = URL(raw.trim()).host
        .removePrefix("[")
        .removeSuffix("]")
        .lowercase()
    host == "localhost" || host == "::1" || host.startsWith("127.")
}.getOrDefault(false)

@Composable
internal fun SetupScreen(onConnect: (String) -> Unit) {
    var raw by remember { mutableStateOf(DEFAULT_SERVER_URL) }
    var error by remember { mutableStateOf<String?>(null) }
    val loopback = remember(raw) { isLoopback(raw) }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
        contentColor = MaterialTheme.colorScheme.onBackground,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
                            Color.Transparent,
                        ),
                        radius = 900f,
                    ),
                ),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .statusBarsPadding()
                    .navigationBarsPadding()
                    .padding(horizontal = 24.dp, vertical = 22.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Surface(
                            modifier = Modifier.size(44.dp),
                            shape = RoundedCornerShape(13.dp),
                            color = MaterialTheme.colorScheme.primary,
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(
                                    "A0",
                                    color = MaterialTheme.colorScheme.onPrimary,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Black,
                                )
                            }
                        }
                        Text(
                            "AGENT ZERO",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onBackground,
                        )
                    }

                    Surface(
                        shape = CircleShape,
                        color = Color.Transparent,
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    ) {
                        Text(
                            "WEBUI",
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }

                Spacer(Modifier.height(56.dp))

                Text(
                    "Your Agent Zero,\nwithout the desktop.",
                    style = MaterialTheme.typography.displaySmall,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.onBackground,
                )
                Text(
                    "Connect directly to the real WebUI. Plugins, auth, WebSockets and custom interfaces stay intact.",
                    modifier = Modifier.padding(top = 14.dp),
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Row(
                    modifier = Modifier.padding(top = 20.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CapabilityChip("PLUGINS")
                    CapabilityChip("WEBSOCKETS")
                    CapabilityChip("HTTP/S")
                }

                Spacer(Modifier.height(44.dp))

                Text(
                    "INSTANCE",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )

                OutlinedTextField(
                    value = raw,
                    onValueChange = {
                        raw = it
                        error = null
                    },
                    label = { Text("Server URL") },
                    placeholder = { Text(DEFAULT_SERVER_URL) },
                    supportingText = error?.let { msg -> { Text(msg) } },
                    isError = error != null,
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 9.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surface,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                    ),
                )

                if (loopback) {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 10.dp),
                        shape = RoundedCornerShape(14.dp),
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                        border = BorderStroke(
                            1.dp,
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.22f),
                        ),
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(3.dp),
                        ) {
                            Text(
                                "Loopback endpoint",
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground,
                            )
                            Text(
                                "Valid for a phone-local service, Termux/OpenSSH -L tunnel, adb reverse, or similar forwarding. The app will not rewrite localhost or 127.x.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
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
                        .padding(top = 16.dp)
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                    ),
                ) {
                    Text("Open Agent Zero", fontWeight = FontWeight.Bold)
                }

                Text(
                    "HTTP is allowed, including loopback and LAN endpoints. TLS is still enforced normally when you choose HTTPS.",
                    modifier = Modifier.padding(top = 13.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Spacer(Modifier.height(24.dp))
            }
        }
    }
}

@Composable
private fun CapabilityChip(label: String) {
    Surface(
        shape = RoundedCornerShape(9.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.8f)),
    ) {
        Text(
            label,
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.SemiBold,
        )
    }
}
