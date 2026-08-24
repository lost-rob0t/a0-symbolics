# A0 Symbolics Android

Native Android shell around the authoritative Agent Zero WebUI. The WebView preserves Agent Zero authentication, WebSockets, service workers, and plugin UI/extension compatibility while the native shell handles server selection and Android platform integration.

Build with `gradle :app:assembleDebug` from this directory, or use the repository Android GitHub Actions workflow. The resulting debug APK is `app/build/outputs/apk/debug/app-debug.apk`.
