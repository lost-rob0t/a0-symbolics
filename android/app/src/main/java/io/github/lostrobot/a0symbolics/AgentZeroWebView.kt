package io.github.lostrobot.a0symbolics

import android.Manifest
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Environment
import android.webkit.CookieManager
import android.webkit.PermissionRequest
import android.webkit.SslErrorHandler
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat

internal class WebController(
    private val server: String,
    initialUrl: String = server,
) {
    internal var view: WebView? = null
    internal var generation by mutableIntStateOf(0)
    var url by mutableStateOf(initialUrl)
    var title by mutableStateOf("Agent Zero")
    var progress by mutableIntStateOf(0)
    var canGoBack by mutableStateOf(false)
    var canGoForward by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)

    fun sync() {
        view?.let {
            url = it.url ?: url
            title = it.title?.takeIf(String::isNotBlank) ?: title
            canGoBack = it.canGoBack()
            canGoForward = it.canGoForward()
        }
    }

    fun back() {
        view?.takeIf { it.canGoBack() }?.goBack()
    }

    fun forward() {
        view?.takeIf { it.canGoForward() }?.goForward()
    }

    fun reload() {
        error = null
        view?.reload() ?: run { generation += 1 }
    }

    fun home() {
        error = null
        url = server
        view?.loadUrl(server) ?: run { generation += 1 }
    }

    fun rendererGone() {
        view = null
        canGoBack = false
        canGoForward = false
        error = "The Android WebView process stopped. Reconnect to restore this page."
    }
}

@Composable
internal fun AgentZeroWebView(
    server: String,
    controller: WebController,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    var fileCb by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    var permissionReq by remember { mutableStateOf<PermissionRequest?>(null) }
    val files = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        fileCb?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data))
        fileCb = null
    }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        val req = permissionReq ?: return@rememberLauncherForActivityResult
        permissionReq = null
        val allowed = req.resources.filter {
            (it == PermissionRequest.RESOURCE_AUDIO_CAPTURE &&
                (grants[Manifest.permission.RECORD_AUDIO] == true ||
                    ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)) ||
                (it == PermissionRequest.RESOURCE_VIDEO_CAPTURE &&
                    (grants[Manifest.permission.CAMERA] == true ||
                        ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED))
        }
        if (allowed.isEmpty()) req.deny() else req.grant(allowed.toTypedArray())
    }

    DisposableEffect(server) {
        onDispose {
            fileCb?.onReceiveValue(null)
            fileCb = null
            permissionReq?.deny()
            permissionReq = null
            controller.view?.destroy()
            controller.view = null
        }
    }

    key(controller.generation) {
        AndroidView(
            factory = { c ->
                WebView(c).apply web@{
                    controller.view = this
                    WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
                    settings.apply {
                        javaScriptEnabled = true
                        domStorageEnabled = true
                        databaseEnabled = true
                        allowFileAccess = false
                        allowContentAccess = true
                        cacheMode = WebSettings.LOAD_DEFAULT
                        mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                        javaScriptCanOpenWindowsAutomatically = true
                        setSupportMultipleWindows(false)
                        mediaPlaybackRequiresUserGesture = false
                        userAgentString = "$userAgentString A0SymbolicsAndroid/${BuildConfig.VERSION_NAME}"
                    }
                    CookieManager.getInstance().apply {
                        setAcceptCookie(true)
                        setAcceptThirdPartyCookies(this@web, true)
                    }
                    webViewClient = object : WebViewClient() {
                        override fun shouldOverrideUrlLoading(v: WebView, r: WebResourceRequest): Boolean {
                            return when (r.url.scheme?.lowercase()) {
                                "http", "https" -> false
                                "mailto", "tel" -> {
                                    runCatching { c.startActivity(Intent(Intent.ACTION_VIEW, r.url)) }
                                    true
                                }
                                else -> true
                            }
                        }

                        override fun onPageStarted(v: WebView, u: String?, f: android.graphics.Bitmap?) {
                            controller.error = null
                            controller.progress = 0
                            controller.sync()
                        }

                        override fun onPageFinished(v: WebView, u: String?) {
                            controller.progress = 100
                            controller.sync()
                            if (u != null && origin(u) == origin(server)) {
                                v.evaluateJavascript(MOBILE_JS, null)
                            }
                        }

                        override fun onReceivedError(v: WebView, r: WebResourceRequest, e: WebResourceError) {
                            if (r.isForMainFrame) {
                                controller.error = e.description?.toString() ?: "Server unreachable"
                            }
                        }

                        override fun onReceivedSslError(
                            v: WebView,
                            handler: SslErrorHandler,
                            error: android.net.http.SslError,
                        ) {
                            handler.cancel()
                            controller.error = "TLS certificate validation failed."
                        }

                        override fun onRenderProcessGone(
                            v: WebView,
                            detail: android.webkit.RenderProcessGoneDetail,
                        ): Boolean {
                            controller.rendererGone()
                            return true
                        }
                    }
                    webChromeClient = object : WebChromeClient() {
                        override fun onProgressChanged(v: WebView, progress: Int) {
                            controller.progress = progress
                            controller.sync()
                        }

                        override fun onShowFileChooser(
                            v: WebView,
                            cb: ValueCallback<Array<Uri>>,
                            params: FileChooserParams,
                        ): Boolean {
                            fileCb?.onReceiveValue(null)
                            fileCb = cb
                            return runCatching {
                                files.launch(params.createIntent())
                                true
                            }.getOrElse {
                                fileCb = null
                                cb.onReceiveValue(null)
                                false
                            }
                        }

                        override fun onPermissionRequest(req: PermissionRequest) {
                            if (origin(req.origin.toString()) != origin(server)) {
                                req.deny()
                                return
                            }
                            val needs = buildList {
                                if (PermissionRequest.RESOURCE_AUDIO_CAPTURE in req.resources) {
                                    add(Manifest.permission.RECORD_AUDIO)
                                }
                                if (PermissionRequest.RESOURCE_VIDEO_CAPTURE in req.resources) {
                                    add(Manifest.permission.CAMERA)
                                }
                            }.toTypedArray()
                            if (needs.isEmpty()) {
                                req.deny()
                            } else {
                                permissionReq?.deny()
                                permissionReq = req
                                permissions.launch(needs)
                            }
                        }

                        override fun onPermissionRequestCanceled(req: PermissionRequest) {
                            if (permissionReq === req) permissionReq = null
                        }
                    }
                    setDownloadListener { u, ua, contentDisposition, mime, _ ->
                        runCatching {
                            val name = URLUtil.guessFileName(u, contentDisposition, mime)
                            val request = DownloadManager.Request(Uri.parse(u))
                                .setMimeType(mime)
                                .addRequestHeader("User-Agent", ua)
                                .addRequestHeader("Cookie", CookieManager.getInstance().getCookie(u).orEmpty())
                                .setTitle(name)
                                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
                            (context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(request)
                        }
                    }
                    loadUrl(controller.url)
                }
            },
            modifier = modifier,
        )
    }
}

private const val MOBILE_JS = """
(() => {
 const root=document.documentElement;
 root.dataset.a0Android='1';
 let v=document.querySelector('meta[name="viewport"]');
 if(!v){v=document.createElement('meta');v.name='viewport';document.head?.appendChild(v)}
 v.content='width=device-width,initial-scale=1,viewport-fit=cover';
 const syncViewport=()=>{
   root.style.setProperty('--a0-android-vh',`${window.visualViewport?.height||window.innerHeight}px`);
   root.style.setProperty('--a0-android-vw',`${window.visualViewport?.width||window.innerWidth}px`);
 };
 syncViewport();
 window.visualViewport?.addEventListener('resize',syncViewport,{passive:true});
 if(!document.getElementById('a0-android-css')){
   const s=document.createElement('style');
   s.id='a0-android-css';
   s.textContent='html[data-a0-android="1"]{overscroll-behavior:none}@media(max-width:700px){html[data-a0-android="1"] input,html[data-a0-android="1"] textarea,html[data-a0-android="1"] select{font-size:max(16px,1em)}}';
   document.head?.appendChild(s)
 }
})();
"""
