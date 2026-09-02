"""Production login surface for app.ilaios.com.

This module adds only the public login UI and delegates all identity, session,
OAuth, Li, and health behavior to the existing canonical AppRuntime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlsplit

from apps.web_app_runtime.server import (
    AppHTTPServer,
    AppRuntime,
    AppRuntimeConfigurationError,
    RuntimeRequest,
    RuntimeResponse,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BRAND_DIR = _REPO_ROOT / "brand" / "assets"
_BRAND_LIGHT = (_BRAND_DIR / "13-ilaios-primary-horizontal-light.jpg").read_bytes()
_BRAND_DARK = (_BRAND_DIR / "02-ilaios-primary-horizontal-dark.jpg").read_bytes()

_LOGIN_HTML = """<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="theme-color" content="#FFFFFF">
  <title>Sign in | ILAIOS</title>
  <link rel="stylesheet" href="/login/styles.css">
</head>
<body>
  <main class="shell">
    <div class="theme-switch" role="group" aria-label="Theme">
      <button class="theme-option is-active" id="theme-light" type="button" aria-pressed="true">
        <span aria-hidden="true">☼</span><span>Light</span>
      </button>
      <span class="theme-divider" aria-hidden="true"></span>
      <button class="theme-option" id="theme-dark" type="button" aria-pressed="false">
        <span aria-hidden="true">◐</span><span>Dark</span>
      </button>
    </div>

    <section class="login-stage" aria-labelledby="login-title">
      <div class="brand-lockup" aria-hidden="true">
        <img class="brand-image brand-image-light" src="/login/brand-light.jpg" alt="">
        <img class="brand-image brand-image-dark" src="/login/brand-dark.jpg" alt="">
      </div>

      <div class="login-card">
        <h1 id="login-title">Sign in to continue</h1>
        <p class="intro">Use your existing account to access ILAIOS.</p>

        <div class="providers" id="providers" aria-live="polite">
          <a class="provider provider-primary" data-provider="google" href="/auth/google/start">
            <span class="provider-mark google-mark" aria-hidden="true">G</span>
            <span>Continue with Google</span>
            <span class="provider-arrow" aria-hidden="true">›</span>
          </a>
          <a class="provider" data-provider="microsoft" href="/auth/microsoft/start">
            <span class="provider-mark microsoft-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
            <span>Continue with Microsoft</span>
            <span class="provider-arrow" aria-hidden="true">›</span>
          </a>
          <a class="provider" data-provider="github" href="/auth/github/start">
            <span class="provider-mark github-mark" aria-hidden="true">GH</span>
            <span>Continue with GitHub</span>
            <span class="provider-arrow" aria-hidden="true">›</span>
          </a>
        </div>
      </div>
    </section>

    <footer class="trust-footer">
      <div class="trust-line"><span class="trust-shield" aria-hidden="true">◇</span> Secure <span>•</span> Private <span>•</span> Built for Trust</div>
      <p>By continuing, you acknowledge the ILAIOS authentication flow and security controls.</p>
    </footer>
  </main>

  <script src="/login/app.js" defer></script>
</body>
</html>
""".encode("utf-8")

_LOGIN_CSS = b""":root {
  color-scheme: light;
  --bg: #FFFFFF;
  --surface: #FFFFFF;
  --surface-elevated: #FFFFFF;
  --text: #0A0A0A;
  --secondary: #4F4F4F;
  --tertiary: #6F6F6F;
  --disabled: #9A9A9A;
  --line: #E2E2E2;
  --line-strong: #CFCFCF;
  --hover: #F3F3F3;
  --active: #EAEAEA;
  --primary: #0A0A0A;
  --primary-text: #FFFFFF;
  --shadow: 0 18px 52px rgba(0,0,0,.07);
}

html[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0A0A0A;
  --surface: #141414;
  --surface-elevated: #1E1E1E;
  --text: #FFFFFF;
  --secondary: #E6E6E6;
  --tertiary: #B3B3B3;
  --disabled: #808080;
  --line: #2A2A2A;
  --line-strong: #2A2A2A;
  --hover: #242424;
  --active: #2F2F2F;
  --primary: #1E1E1E;
  --primary-text: #FFFFFF;
  --shadow: none;
}

* { box-sizing: border-box; }
html, body { width: 100%; min-height: 100%; }
body {
  margin: 0;
  min-height: 100dvh;
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}
button, a { font: inherit; }

.shell {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  display: grid;
  grid-template-rows: 1fr auto;
}

.theme-switch {
  position: absolute;
  z-index: 3;
  top: 24px;
  right: 28px;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  padding: 4px 6px;
  border-radius: 26px;
  border: 1px solid var(--line);
  background: var(--surface);
}
.theme-option {
  min-height: 38px;
  padding: 0 15px;
  border: 0;
  border-radius: 21px;
  background: transparent;
  color: var(--tertiary);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  font-weight: 650;
}
.theme-option:hover { background: var(--hover); color: var(--text); }
.theme-option.is-active { color: var(--text); background: var(--active); }
.theme-divider { width: 1px; height: 24px; background: var(--line); }

.login-stage {
  width: 100%;
  min-height: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 24px;
  padding: 84px 24px 32px;
  text-align: center;
}

.brand-lockup {
  width: min(300px, 62vw);
  aspect-ratio: 3 / 1;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.brand-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
}
.brand-image-dark { display: none; }
html[data-theme="dark"] .brand-image-light { display: none; }
html[data-theme="dark"] .brand-image-dark { display: block; }

.login-card {
  width: min(100%, 520px);
  padding: 34px 34px 32px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

h1 {
  margin: 0;
  font-size: clamp(34px, 4vw, 46px);
  line-height: 1.08;
  letter-spacing: -0.042em;
}
.intro {
  margin: 14px 0 30px;
  color: var(--secondary);
  font-size: 17px;
  line-height: 1.5;
}
.providers { display: grid; gap: 12px; }
.provider {
  min-height: 62px;
  border: 1px solid var(--line);
  border-radius: 14px;
  display: grid;
  grid-template-columns: 38px 1fr 24px;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  text-decoration: none;
  text-align: left;
  background: var(--surface-elevated);
  color: var(--text);
  font-size: 17px;
  font-weight: 650;
  transition: border-color 120ms ease, background-color 120ms ease, transform 120ms ease;
}
.provider:hover { background: var(--hover); border-color: var(--line-strong); transform: translateY(-1px); }
.provider:active { background: var(--active); transform: translateY(0); }
.provider-primary { background: var(--primary); color: var(--primary-text); border-color: var(--primary); }
.provider-primary:hover { background: #242424; border-color: #242424; }
.provider-primary:active { background: #2F2F2F; border-color: #2F2F2F; }
html[data-theme="dark"] .provider-primary { background: #1E1E1E; border-color: #2A2A2A; color: #FFFFFF; }
html[data-theme="dark"] .provider-primary:hover { background: #242424; border-color: #2A2A2A; }
html[data-theme="dark"] .provider-primary:active { background: #2F2F2F; border-color: #2A2A2A; }
.provider-mark { width: 32px; height: 32px; display: grid; place-items: center; font-weight: 800; }
.google-mark { font-size: 24px; color: #4285F4; }
.github-mark { width: 32px; height: 32px; border-radius: 50%; background: currentColor; color: var(--surface-elevated); font-size: 9px; }
.provider-primary .google-mark { background: transparent; }
html[data-theme="dark"] .github-mark { color: #FFFFFF; background: #FFFFFF; color: #1E1E1E; }
.microsoft-mark { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; padding: 5px; }
.microsoft-mark i:nth-child(1) { background: #F25022; }
.microsoft-mark i:nth-child(2) { background: #7FBA00; }
.microsoft-mark i:nth-child(3) { background: #00A4EF; }
.microsoft-mark i:nth-child(4) { background: #FFB900; }
.microsoft-mark i { width: 10px; height: 10px; display: block; }
.provider-arrow { justify-self: end; font-size: 30px; font-weight: 300; line-height: 1; }
.provider[aria-disabled="true"] { color: var(--disabled); opacity: 1; pointer-events: none; }

.theme-option:focus-visible,
.provider:focus-visible { outline: 2px solid var(--secondary); outline-offset: 3px; }

.trust-footer {
  padding: 12px 20px 22px;
  text-align: center;
  color: var(--tertiary);
  font-size: 14px;
}
.trust-line { color: var(--secondary); font-weight: 600; display: flex; justify-content: center; gap: 8px; align-items: center; }
.trust-shield { color: var(--secondary); font-size: 18px; }
.trust-footer p { max-width: 520px; margin: 7px auto 0; line-height: 1.45; }

html[data-theme="dark"] .brand-lockup { background: #0A0A0A; }
html[data-theme="dark"] .login-card { background: #141414; }

@media (max-height: 760px) and (min-width: 761px) {
  .login-stage { gap: 16px; padding-top: 68px; padding-bottom: 18px; }
  .brand-lockup { width: 230px; }
  .login-card { padding: 26px 30px 26px; }
  h1 { font-size: 36px; }
  .intro { margin: 10px 0 22px; font-size: 16px; }
  .provider { min-height: 56px; }
  .trust-footer { padding-bottom: 14px; }
}

@media (max-width: 760px) {
  body { overflow-y: auto; }
  .shell { min-height: 100dvh; }
  .theme-switch { top: 16px; right: 16px; min-height: 42px; }
  .theme-option { min-height: 32px; padding: 0 10px; }
  .theme-option span:last-child { display: none; }
  .login-stage { min-height: 100dvh; gap: 18px; padding: 78px 16px 92px; }
  .brand-lockup { width: min(240px, 70vw); }
  .login-card { width: min(100%, 480px); padding: 28px 20px 24px; border-radius: 18px; }
  h1 { font-size: 34px; }
  .intro { font-size: 15px; margin: 12px 0 24px; }
  .provider { min-height: 58px; font-size: 16px; padding: 0 14px; }
  .trust-footer { position: absolute; left: 0; right: 0; bottom: 0; padding: 12px 12px 18px; font-size: 12px; }
  .trust-footer p { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}
"""

_LOGIN_JS = b"""(function(){\"use strict\";
const root=document.documentElement;
const lightButton=document.getElementById('theme-light');
const darkButton=document.getElementById('theme-dark');
function storedTheme(){try{return localStorage.getItem('ilaios-theme');}catch(_error){return null;}}
function storeTheme(value){try{localStorage.setItem('ilaios-theme',value);}catch(_error){return;}}
function apply(theme){const value=theme==='dark'?'dark':'light';root.dataset.theme=value;const dark=value==='dark';lightButton.classList.toggle('is-active',!dark);darkButton.classList.toggle('is-active',dark);lightButton.setAttribute('aria-pressed',String(!dark));darkButton.setAttribute('aria-pressed',String(dark));const meta=document.querySelector('meta[name=theme-color]');if(meta){meta.setAttribute('content',dark?'#0A0A0A':'#FFFFFF');}}
apply(storedTheme()==='dark'?'dark':'light');
lightButton.addEventListener('click',function(){apply('light');storeTheme('light');});
darkButton.addEventListener('click',function(){apply('dark');storeTheme('dark');});
fetch('/auth/providers',{credentials:'same-origin',cache:'no-store'}).then(function(response){if(!response.ok){return null;}return response.json();}).then(function(payload){if(!payload||!Array.isArray(payload.providers)){return;}const available=new Set(payload.providers);for(const link of document.querySelectorAll('[data-provider]')){const provider=link.getAttribute('data-provider');if(!available.has(provider)){link.setAttribute('aria-disabled','true');link.setAttribute('tabindex','-1');link.removeAttribute('href');}}}).catch(function(){return;});
})();
"""


class LoginAppRuntime(AppRuntime):
    """Add a bounded public login surface while preserving canonical auth runtime."""

    def dispatch(
        self,
        request: RuntimeRequest,
        *,
        now: datetime | None = None,
    ) -> RuntimeResponse:
        split = urlsplit(request.target)
        method = request.method.strip().upper()
        if split.path == "/":
            if method != "GET":
                return self._method_not_allowed("GET")
            if split.query:
                return self._json_error(
                    HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                )
            return self._asset_response(
                _LOGIN_HTML,
                "text/html; charset=utf-8",
                csp=(
                    "default-src 'none'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                    "frame-ancestors 'none'; form-action 'self'"
                ),
            )
        if split.path == "/login/styles.css":
            if method != "GET":
                return self._method_not_allowed("GET")
            if split.query:
                return self._json_error(
                    HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                )
            return self._asset_response(_LOGIN_CSS, "text/css; charset=utf-8")
        if split.path == "/login/app.js":
            if method != "GET":
                return self._method_not_allowed("GET")
            if split.query:
                return self._json_error(
                    HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                )
            return self._asset_response(_LOGIN_JS, "text/javascript; charset=utf-8")
        if split.path == "/login/brand-light.jpg":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._asset_response(_BRAND_LIGHT, "image/jpeg")
        if split.path == "/login/brand-dark.jpg":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._asset_response(_BRAND_DARK, "image/jpeg")
        return super().dispatch(request, now=now)

    @staticmethod
    def _asset_response(
        body: bytes,
        content_type: str,
        *,
        csp: str | None = None,
    ) -> RuntimeResponse:
        headers: tuple[tuple[str, str], ...] = (
            ("Content-Type", content_type),
            ("Cache-Control", "no-store"),
        )
        if csp is not None:
            headers += (("Content-Security-Policy", csp),)
        return RuntimeResponse(status=HTTPStatus.OK, body=body, headers=headers)


def build_runtime(env: Mapping[str, str] | None = None) -> LoginAppRuntime:
    """Build the login-enabled runtime from process environment."""
    runtime = LoginAppRuntime.from_environment(os.environ if env is None else env)
    if not isinstance(runtime, LoginAppRuntime):
        raise AppRuntimeConfigurationError("login runtime composition failed")
    return runtime


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise AppRuntimeConfigurationError("runtime does not accept CLI arguments")
    runtime = build_runtime()
    server = AppHTTPServer(
        (runtime.environment.host, runtime.environment.port),
        runtime,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
