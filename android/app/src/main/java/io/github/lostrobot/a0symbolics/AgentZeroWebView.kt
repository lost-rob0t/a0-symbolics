package io.github.lostrobot.a0symbolics

import android.Manifest
import android.app.DownloadManager
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Environment
import android.webkit.*
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat

internal class WebController(private val server: String) {
    internal var view: WebView? = null
    var url by mutableStateOf(server)
    var title by mutableStateOf("Agent Zero")
    var progress by mutableIntStateOf(0)
    var canGoBack by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    fun sync() { view?.let { url = it.url ?: url; title = it.title?.takeIf(String::isNotBlank) ?: title; canGoBack = it.canGoBack() } }
    fun back() { view?.takeIf { it.canGoBack() }?.goBack() }
    fun reload() { error = null; view?.reload() }
    fun home() { error = null; view?.loadUrl(server) }
}

@Composable
internal fun AgentZeroWebView(server: String, controller: WebController, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var fileCb by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    var permissionReq by remember { mutableStateOf<PermissionRequest?>(null) }
    val files = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        fileCb?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)); fileCb = null
    }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        val req = permissionReq ?: return@rememberLauncherForActivityResult
        permissionReq = null
        val allowed = req.resources.filter {
            (it == PermissionRequest.RESOURCE_AUDIO_CAPTURE && (grants[Manifest.permission.RECORD_AUDIO] == true || ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)) ||
            (it == PermissionRequest.RESOURCE_VIDEO_CAPTURE && (grants[Manifest.permission.CAMERA] == true || ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED))
        }
        if (allowed.isEmpty()) req.deny() else req.grant(allowed.toTypedArray())
    }

    DisposableEffect(server) {
        onDispose { controller.view?.destroy(); controller.view = null }
    }

    AndroidView(modifier, factory = { c ->
        WebView(c).apply w@{
            controller.view = this
            WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
            settings.apply {
                javaScriptEnabled = true; domStorageEnabled = true; databaseEnabled = true
                allowFileAccess = false; allowContentAccess = true; cacheMode = WebSettings.LOAD_DEFAULT
                mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                javaScriptCanOpenWindowsAutomatically = true; setSupportMultipleWindows(false)
                mediaPlaybackRequiresUserGesture = false
                userAgentString = "$userAgentString A0SymbolicsAndroid/${BuildConfig.VERSION_NAME}"
            }
            CookieManager.getInstance().apply { setAcceptCookie(true); setAcceptThirdPartyCookies(this@w, true) }
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(v: WebView, r: WebResourceRequest) = r.url.scheme?.lowercase() !in setOf("http", "https")
                override fun onPageStarted(v: WebView, u: String?, f: android.graphics.Bitmap?) { controller.error = null; controller.sync() }
                override fun onPageFinished(v: WebView, u: String?) {
                    controller.progress = 100; controller.sync()
                    if (u != null && origin(u) == origin(server)) v.evaluateJavascript(MOBILE_JS, null)
                }
                override fun onReceivedError(v: WebView, r: WebResourceRequest, e: WebResourceError) { if (r.isForMainFrame) controller.error = e.description?.toString() ?: "Server unreachable" }
                override fun onReceivedSslError(v: WebView, h: SslErrorHandler, e: android.net.http.SslError) { h.cancel(); controller.error = "TLS certificate validation failed." }
                override fun onRenderProcessGone(v: WebView, d: android.webkit.RenderProcessGoneDetail): Boolean { controller.error = "WebView stopped. Reconnect to recover."; controller.view = null; return true }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(v: WebView, p: Int) { controller.progress = p; controller.sync() }
                override fun onShowFileChooser(v: WebView, cb: ValueCallback<Array<Uri>>, p: FileChooserParams): Boolean {
                    fileCb?.onReceiveValue(null); fileCb = cb
                    return runCatching { files.launch(p.createIntent()); true }.getOrElse { fileCb = null; cb.onReceiveValue(null); false }
                }
                override fun onPermissionRequest(req: PermissionRequest) {
                    if (origin(req.origin.toString()) != origin(server)) { req.deny(); return }
                    val needs = buildList {
                        if (PermissionRequest.RESOURCE_AUDIO_CAPTURE in req.resources) add(Manifest.permission.RECORD_AUDIO)
                        if (PermissionRequest.RESOURCE_VIDEO_CAPTURE in req.resources) add(Manifest.permission.CAMERA)
                    }.toTypedArray()
                    if (needs.isEmpty()) req.deny() else { permissionReq = req; permissions.launch(needs) }
                }
            }
            setDownloadListener { u, ua, cd, mime, _ ->
                runCatching {
                    val name = URLUtil.guessFileName(u, cd, mime)
                    val req = DownloadManager.Request(Uri.parse(u)).setMimeType(mime)
                        .addRequestHeader("User-Agent", ua).addRequestHeader("Cookie", CookieManager.getInstance().getCookie(u).orEmpty())
                        .setTitle(name).setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                        .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
                    (context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(req)
                }
            }
            loadUrl(server)
        }
    })
}

private const val MOBILE_JS = """
(() => {
 document.documentElement.dataset.a0Android='1';
 let v=document.querySelector('meta[name="viewport"]');
 if(!v){v=document.createElement('meta');v.name='viewport';document.head?.appendChild(v)}
 v.content='width=device-width,initial-scale=1,viewport-fit=cover';
 if(!document.getElementById('a0-android-css')){let s=document.createElement('style');s.id='a0-android-css';s.textContent='html[data-a0-android="1"]{overscroll-behavior:none}@media(max-width:700px){html[data-a0-android="1"] input,html[data-a0-android="1"] textarea,html[data-a0-android="1"] select{font-size:max(16px,1em)}}';document.head?.appendChild(s)}
})();
"""
