package io.github.lostrobot.a0symbolics

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SetupScreen(
    initialUrl: String = DEFAULT_SERVER_URL,
    onConnect: (String) -> Unit,
    onCancel: (() -> Unit)? = null,
) {
    var raw by remember(initialUrl) { mutableStateOf(initialUrl) }
    var error by remember { mutableStateOf<String?>(null) }
    val loopback = remember(raw) { isLoopback(raw) }
    val insecure = remember(raw) { raw.trim().startsWith("http://", ignoreCase = true) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Agent Zero", fontWeight = FontWeight.Bold)
                        Text(
                            "Instance settings",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                navigationIcon = {
                    if (onCancel != null) {
                        IconButton(onClick = onCancel) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .navigationBarsPadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Surface(
                    modifier = Modifier.size(54.dp),
                    shape = RoundedCornerShape(16.dp),
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
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(
                        "Connect to Agent Zero",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "The app shell connects to the real Agent Zero WebUI.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(22.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f),
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(
                        "SERVER",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                    OutlinedTextField(
                        value = raw,
                        onValueChange = {
                            raw = it
                            error = null
                        },
                        label = { Text("Agent Zero URL") },
                        placeholder = { Text(DEFAULT_SERVER_URL) },
                        supportingText = error?.let { msg -> { Text(msg) } },
                        isError = error != null,
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                    )

                    ConnectionNotice(loopback = loopback, insecure = insecure)

                    Button(
                        onClick = {
                            normalizeUrl(raw)
                                .onSuccess(onConnect)
                                .onFailure { error = it.message ?: "Invalid URL" }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(54.dp),
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Text("Connect", fontWeight = FontWeight.Bold)
                    }
                }
            }

            Text(
                "Authentication stays inside Agent Zero. This app does not store your Agent Zero password, API keys, or CSRF credentials.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun ConnectionNotice(loopback: Boolean, insecure: Boolean) {
    val title: String
    val body: String
    val warning: Boolean
    when {
        loopback -> {
            title = "Phone-local endpoint"
            body = "Works with Agent Zero running on the phone, a Termux/OpenSSH tunnel, adb reverse, or another loopback forward."
            warning = false
        }
        insecure -> {
            title = "Unencrypted HTTP"
            body = "Use this only on a trusted LAN or tunnel. HTTPS certificate failures are never bypassed."
            warning = true
        }
        else -> {
            title = "HTTPS connection"
            body = "Android will use normal certificate validation and keep Agent Zero authentication in the WebUI."
            warning = false
        }
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = if (warning) {
            MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.58f)
        } else {
            MaterialTheme.colorScheme.surface
        },
        border = BorderStroke(
            1.dp,
            if (warning) MaterialTheme.colorScheme.error.copy(alpha = 0.35f)
            else MaterialTheme.colorScheme.outlineVariant,
        ),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Icon(
                imageVector = if (warning) Icons.Default.Warning else Icons.Default.Lock,
                contentDescription = null,
                tint = if (warning) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            )
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, fontWeight = FontWeight.SemiBold)
                Text(
                    body,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
