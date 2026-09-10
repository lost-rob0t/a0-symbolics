package io.github.lostrobot.a0symbolics

import android.content.Intent
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.BottomSheetDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.net.URL

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SessionScreen(
    server: String,
    themeMode: ThemeMode,
    dynamicColor: Boolean,
    onChangeServer: () -> Unit,
    onThemeModeChange: (ThemeMode) -> Unit,
    onDynamicColorChange: (Boolean) -> Unit,
) {
    var restoredUrl by rememberSaveable(server) { mutableStateOf(server) }
    val controller = remember(server) { WebController(server, restoredUrl) }
    var showControls by remember { mutableStateOf(false) }
    val context = LocalContext.current

    LaunchedEffect(controller.url) { restoredUrl = controller.url }
    BackHandler(enabled = controller.canGoBack) { controller.back() }

    Scaffold(
        topBar = {
            TopAppBar(
                navigationIcon = {
                    if (controller.canGoBack) {
                        IconButton(onClick = controller::back) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    }
                },
                title = {
                    Column {
                        Text(
                            controller.title.ifBlank { "Agent Zero" },
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            displayServer(server),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    if (server.startsWith("http://", ignoreCase = true)) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = "Unencrypted HTTP connection",
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.padding(horizontal = 4.dp),
                        )
                    }
                    IconButton(onClick = { showControls = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "App controls")
                    }
                },
            )
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            AgentZeroWebView(
                server = server,
                controller = controller,
                modifier = Modifier.fillMaxSize(),
            )

            if (controller.progress in 1..99) {
                LinearProgressIndicator(
                    progress = { controller.progress / 100f },
                    modifier = Modifier
                        .fillMaxWidth()
                        .align(Alignment.TopCenter),
                )
            }

            controller.error?.let { message ->
                OfflineState(
                    message = message,
                    onRetry = controller::reload,
                    onChangeServer = onChangeServer,
                )
            }
        }
    }

    if (showControls) {
        ModalBottomSheet(
            onDismissRequest = { showControls = false },
            dragHandle = { BottomSheetDefaults.DragHandle() },
        ) {
            SessionControls(
                server = server,
                controller = controller,
                themeMode = themeMode,
                dynamicColor = dynamicColor,
                onThemeModeChange = onThemeModeChange,
                onDynamicColorChange = onDynamicColorChange,
                onShare = {
                    val intent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, controller.url)
                    }
                    context.startActivity(Intent.createChooser(intent, "Share Agent Zero"))
                },
                onChangeServer = {
                    showControls = false
                    onChangeServer()
                },
            )
        }
    }
}

@Composable
private fun OfflineState(
    message: String,
    onRetry: () -> Unit,
    onChangeServer: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier.padding(32.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Surface(
                modifier = Modifier.size(64.dp),
                shape = RoundedCornerShape(22.dp),
                color = MaterialTheme.colorScheme.surfaceVariant,
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        Icons.Default.CloudOff,
                        contentDescription = null,
                        modifier = Modifier.size(30.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            Text(
                "Agent Zero is offline",
                modifier = Modifier.padding(top = 20.dp),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                message,
                modifier = Modifier.padding(top = 8.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(
                onClick = onRetry,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 24.dp),
            ) {
                Text("Reconnect")
            }
            OutlinedButton(
                onClick = onChangeServer,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
            ) {
                Text("Change instance")
            }
        }
    }
}

@Composable
private fun SessionControls(
    server: String,
    controller: WebController,
    themeMode: ThemeMode,
    dynamicColor: Boolean,
    onThemeModeChange: (ThemeMode) -> Unit,
    onDynamicColorChange: (Boolean) -> Unit,
    onShare: () -> Unit,
    onChangeServer: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(bottom = 16.dp),
    ) {
        Text(
            "Session",
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Text(
            displayServer(server),
            modifier = Modifier.padding(horizontal = 20.dp),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 18.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            SessionAction(
                icon = Icons.AutoMirrored.Filled.ArrowBack,
                label = "Back",
                enabled = controller.canGoBack,
                onClick = controller::back,
            )
            SessionAction(
                icon = Icons.AutoMirrored.Filled.ArrowForward,
                label = "Forward",
                enabled = controller.canGoForward,
                onClick = controller::forward,
            )
            SessionAction(icon = Icons.Default.Home, label = "Home", onClick = controller::home)
            SessionAction(icon = Icons.Default.Refresh, label = "Reload", onClick = controller::reload)
        }

        HorizontalDivider()
        ListItem(
            headlineContent = { Text("Share current page") },
            supportingContent = { Text("Use Android's share sheet") },
            leadingContent = { Icon(Icons.Default.Share, contentDescription = null) },
            modifier = Modifier.clickable(onClick = onShare),
        )
        ListItem(
            headlineContent = { Text("Change Agent Zero instance") },
            supportingContent = { Text("Switch the server without clearing this setting first") },
            leadingContent = {
                Surface(
                    modifier = Modifier.size(32.dp),
                    shape = RoundedCornerShape(10.dp),
                    color = MaterialTheme.colorScheme.primaryContainer,
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            "A0",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Black,
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                        )
                    }
                }
            },
            modifier = Modifier.clickable(onClick = onChangeServer),
        )

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
        Text(
            "Appearance",
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
        )
        Row(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            ThemeMode.entries.forEach { mode ->
                FilterChip(
                    selected = themeMode == mode,
                    onClick = { onThemeModeChange(mode) },
                    label = {
                        Text(
                            when (mode) {
                                ThemeMode.SYSTEM -> "System"
                                ThemeMode.DARK -> "Dark"
                                ThemeMode.LIGHT -> "Light"
                            },
                        )
                    },
                )
            }
        }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("Dynamic color", fontWeight = FontWeight.Medium)
                Text(
                    "Use the phone's Material color palette when supported.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(checked = dynamicColor, onCheckedChange = onDynamicColorChange)
        }
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
private fun SessionAction(
    icon: ImageVector,
    label: String,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        FilledTonalIconButton(onClick = onClick, enabled = enabled) {
            Icon(icon, contentDescription = label)
        }
        Text(
            label,
            modifier = Modifier.padding(top = 5.dp),
            style = MaterialTheme.typography.labelSmall,
            color = if (enabled) MaterialTheme.colorScheme.onSurface
            else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f),
        )
    }
}

private fun displayServer(server: String): String = runCatching {
    val url = URL(server)
    buildString {
        append(url.host.ifBlank { server })
        if (url.port >= 0) append(":${url.port}")
    }
}.getOrDefault(server)
