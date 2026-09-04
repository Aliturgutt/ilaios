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
    <div class="theme-control" role="group" aria-label="Theme">
      <button class="theme-button is-active" id="theme-light" type="button" aria-pressed="true">Light</button>
      <button class="theme-button" id="theme-dark" type="button" aria-pressed="false">Dark</button>
    </div>

    <section class="auth" aria-labelledby="login-title">
      <div class="brand-lockup" aria-label="ILAIOS">
        <img class="brand-image brand-image-light" src="/login/brand-light.jpg" alt="ILAIOS">
        <img class="brand-image brand-image-dark" src="/login/brand-dark.jpg" alt="ILAIOS">
      </div>

      <h1 id="login-title">Welcome back</h1>
      <p class="intro">Choose an account to continue.</p>

      <div class="providers" id="providers" aria-live="polite">
        <a class="provider" data-provider="google" href="/auth/google/start">
          <svg class="provider-logo google-logo" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
            <path fill="#4285F4" d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.482h4.844c-.209 1.125-.843 2.078-1.797 2.716v2.258h2.909c1.702-1.567 2.684-3.874 2.684-6.615z"/>
            <path fill="#34A853" d="M9 18c2.43 0 4.468-.806 5.956-2.18l-2.909-2.258c-.806.54-1.836.859-3.047.859-2.344 0-4.328-1.584-5.037-3.714H.956v2.332A9 9 0 0 0 9 18z"/>
            <path fill="#FBBC05" d="M3.963 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.168.281-1.707V4.961H.956A9 9 0 0 0 0 9c0 1.452.347 2.824.956 4.039l3.007-2.332z"/>
            <path fill="#EA4335" d="M9 3.579c1.321 0 2.507.454 3.441 1.346l2.582-2.582C13.464.89 11.426 0 9 0A9 9 0 0 0 .956 4.961l3.007 2.332C4.672 5.163 6.656 3.579 9 3.579z"/>
          </svg>
          <span>Continue with Google</span>
        </a>

        <a class="provider" data-provider="microsoft" href="/auth/microsoft/start">
          <svg class="provider-logo microsoft-logo" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="1" y="1" width="10" height="10" fill="#F25022"/>
            <rect x="13" y="1" width="10" height="10" fill="#7FBA00"/>
            <rect x="1" y="13" width="10" height="10" fill="#00A4EF"/>
            <rect x="13" y="13" width="10" height="10" fill="#FFB900"/>
          </svg>
          <span>Continue with Microsoft</span>
        </a>

        <a class="provider" data-provider="github" href="/auth/github/start">
          <svg class="provider-logo github-logo" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path fill="currentColor" d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.84 1.237 1.84 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.303-5.466-1.332-5.466-5.93 0-1.31.469-2.381 1.236-3.221-.124-.303-.536-1.523.117-3.176 0 0 1.008-.322 3.301 1.23A11.52 11.52 0 0 1 12 5.803c1.02.005 2.047.138 3.003.404 2.291-1.552 3.297-1.23 3.297-1.23.655 1.653.243 2.873.12 3.176.77.84 1.235 1.911 1.235 3.221 0 4.61-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .315.216.694.825.576C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12z"/>
          </svg>
          <span>Continue with GitHub</span>
        </a>
      </div>

      <p class="notice">By continuing, you acknowledge the ILAIOS authentication and security controls.</p>
    </section>
  </main>
  <script src="/login/app.js" defer></script>
</body>
</html>
""".encode("utf-8")

_LOGIN_CSS = b""":root {
  color-scheme: light;
  --bg:#FFFFFF;
  --text:#111111;
  --muted:#777777;
  --line:#D9D9D9;
  --line-hover:#BEBEBE;
  --button:#FFFFFF;
  --button-hover:#F7F7F7;
  --button-active:#F0F0F0;
  --disabled:#A0A0A0;
}
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0A0A0A;
  --text:#FFFFFF;
  --muted:#B3B3B3;
  --line:#2A2A2A;
  --line-hover:#3A3A3A;
  --button:#141414;
  --button-hover:#242424;
  --button-active:#2F2F2F;
  --disabled:#808080;
}
*{box-sizing:border-box}
html,body{width:100%;min-height:100%}
body{margin:0;min-height:100dvh;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
button,a{font:inherit}
.shell{position:relative;min-height:100dvh;display:grid;place-items:center;padding:48px 20px;background:var(--bg)}
.theme-control{position:fixed;top:20px;right:22px;display:inline-flex;gap:4px;padding:3px;border:1px solid var(--line);border-radius:10px;background:var(--bg)}
.theme-button{height:30px;padding:0 9px;border:0;border-radius:7px;background:transparent;color:var(--muted);font-size:12px;font-weight:600;cursor:pointer}
.theme-button:hover{color:var(--text);background:var(--button-hover)}
.theme-button.is-active{color:var(--text);background:var(--button-active)}
.auth{width:min(100%,384px);text-align:center}
.brand-lockup{width:218.5px;height:73.6px;margin:0 auto 30px;overflow:hidden;background:var(--bg)}
.brand-image{display:block;width:100%;height:100%;object-fit:contain;object-position:center;background:var(--bg)}
.brand-image-dark{display:none;background:#0A0A0A}
html[data-theme="dark"] .brand-image-light{display:none}
html[data-theme="dark"] .brand-image-dark{display:block}
html[data-theme="dark"] .brand-lockup{background:#0A0A0A}
h1{margin:0;font-family:"Segoe UI Variable Display","Segoe UI",Inter,ui-sans-serif,sans-serif;font-size:27px;line-height:1.2;letter-spacing:-.012em;font-weight:600}
.intro{margin:10px 0 28px;color:var(--muted);font-size:14px;line-height:1.45}
.providers{display:grid;gap:10px}
.provider{height:48px;display:grid;grid-template-columns:24px 1fr 24px;align-items:center;padding:0 14px;border:1px solid var(--line);border-radius:8px;background:var(--button);color:var(--text);text-decoration:none;font-size:14px;font-weight:550;text-align:center;transition:background-color 120ms ease,border-color 120ms ease}
.provider::after{content:"";width:24px;height:1px}
.provider:hover{background:var(--button-hover);border-color:var(--line-hover)}
.provider:active{background:var(--button-active)}
.provider-logo{display:block;justify-self:start;width:20px;height:20px;overflow:visible}
.google-logo{width:19px;height:19px}
.microsoft-logo{width:18px;height:18px}
.github-logo{width:20px;height:20px;color:var(--text)}
.provider[aria-disabled="true"]{color:var(--disabled);pointer-events:none}
.theme-button:focus-visible,.provider:focus-visible{outline:2px solid var(--text);outline-offset:2px}
.notice{max-width:350px;margin:22px auto 0;color:var(--muted);font-size:11px;line-height:1.55}
@media (max-width:560px){.shell{padding:72px 18px 32px}.theme-control{top:14px;right:14px}.auth{width:min(100%,360px)}.brand-lockup{width:197.8px;height:66.7px;margin-bottom:24px}h1{font-size:25px}.intro{margin-bottom:24px}.provider{height:48px}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important}}
"""

_LOGIN_JS = b"""(function(){\"use strict\";
const root=document.documentElement;const lightButton=document.getElementById('theme-light');const darkButton=document.getElementById('theme-dark');
function storedTheme(){try{return localStorage.getItem('ilaios-theme');}catch(_error){return null;}}
function storeTheme(value){try{localStorage.setItem('ilaios-theme',value);}catch(_error){return;}}
function apply(theme){const value=theme==='dark'?'dark':'light';root.dataset.theme=value;const dark=value==='dark';lightButton.classList.toggle('is-active',!dark);darkButton.classList.toggle('is-active',dark);lightButton.setAttribute('aria-pressed',String(!dark));darkButton.setAttribute('aria-pressed',String(dark));const meta=document.querySelector('meta[name=theme-color]');if(meta){meta.setAttribute('content',dark?'#0A0A0A':'#FFFFFF');}}
apply(storedTheme()==='dark'?'dark':'light');lightButton.addEventListener('click',function(){apply('light');storeTheme('light');});darkButton.addEventListener('click',function(){apply('dark');storeTheme('dark');});
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
                return self._json_error(HTTPStatus.BAD_REQUEST, "unexpected query parameters")
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
                return self._json_error(HTTPStatus.BAD_REQUEST, "unexpected query parameters")
            return self._asset_response(_LOGIN_CSS, "text/css; charset=utf-8")
        if split.path == "/login/app.js":
            if method != "GET":
                return self._method_not_allowed("GET")
            if split.query:
                return self._json_error(HTTPStatus.BAD_REQUEST, "unexpected query parameters")
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
    server = AppHTTPServer((runtime.environment.host, runtime.environment.port), runtime)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
