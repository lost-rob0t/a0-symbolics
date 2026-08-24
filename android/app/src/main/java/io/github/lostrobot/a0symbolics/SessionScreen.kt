package io.github.lostrobot.a0symbolics

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

@Composable
internal fun SessionScreen(server: String, onChangeServer: () -> Unit) {
    val controller = remember(server) { WebController(server) }
    var expanded by remember { mutableStateOf(false) }
    BackHandler(enabled = controller.canGoBack) { controller.back() }

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        AgentZeroWebView(server, controller, Modifier.fillMaxSize())
        if (controller.progress in 1..99) {
            LinearProgressIndicator(progress = { controller.progress / 100f }, modifier = Modifier.fillMaxWidth().statusBarsPadding())
        }
        Surface(
            modifier = Modifier.align(Alignment.TopCenter).statusBarsPadding().padding(8.dp),
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface.copy(alpha = .95f),
            shadowElevation = 8.dp,
        ) {
            if (!expanded) {
                FilledTonalButton(onClick = { expanded = true }) {
                    Text(if (server.startsWith("http://")) "⚠ Agent Zero" else "● Agent Zero")
                }
            } else {
                Column(Modifier.padding(10.dp)) {
                    Text(controller.title, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Bold)
                    Text(controller.url, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        FilledTonalButton(onClick = controller::back, enabled = controller.canGoBack) { Text("Back") }
                        FilledTonalButton(onClick = controller::reload) { Text("Reload") }
                        FilledTonalButton(onClick = controller::home) { Text("Home") }
                    }
                    Row(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        OutlinedButton(onClick = onChangeServer) { Text("Server") }
                        OutlinedButton(onClick = { expanded = false }) { Text("Hide") }
                    }
                }
            }
        }
        controller.error?.let { msg ->
            Card(Modifier.align(Alignment.Center).padding(24.dp), shape = RoundedCornerShape(26.dp)) {
                Column(Modifier.padding(22.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Can't reach Agent Zero", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(msg, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp))
                    Row(Modifier.padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = controller::reload) { Text("Retry") }
                        OutlinedButton(onClick = onChangeServer) { Text("Server") }
                    }
                }
            }
        }
    }
}
