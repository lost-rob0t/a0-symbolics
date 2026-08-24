# Android App DOX

## Purpose
Own the native Android shell around Agent Zero's authoritative WebUI.

## Local Contracts
- Preserve Agent Zero cookies, CSRF, WebSockets, service workers, plugin pages, and plugin WebUI extensions.
- HTTP and HTTPS endpoints are supported; HTTP is visibly marked insecure.
- Never bypass TLS certificate failures.
- Never expose a generic JavaScript bridge.
- Camera and microphone grants are allowed only for the configured Agent Zero origin.
- Mobile WebView adjustments must be additive and must not rewrite arbitrary plugin DOM.

## Verification
Run `gradle testDebugUnitTest lintDebug assembleDebug` when tests exist; the CI release gate must at least run `lintDebug assembleDebug` and upload the debug APK.
