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
  <meta name="theme-color" content="#f8faff">
  <title>Sign in | ILAIOS</title>
  <link rel="stylesheet" href="/login/styles.css">
</head>
<body>
  <div class="ambient ambient-left" aria-hidden="true"></div>
  <div class="ambient ambient-right" aria-hidden="true"></div>
  <div class="orbit orbit-one" aria-hidden="true"></div>
  <div class="orbit orbit-two" aria-hidden="true"></div>
  <div class="orbit orbit-three" aria-hidden="true"></div>

  <main class="shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="ILAIOS home">
        <img class="brand-image brand-image-light" src="/login/brand-light.jpg" alt="ILAIOS">
        <img class="brand-image brand-image-dark" src="/login/brand-dark.jpg" alt="ILAIOS">
      </a>

      <div class="theme-switch" role="group" aria-label="Theme">
        <button class="theme-option is-active" id="theme-light" type="button" aria-pressed="true">
          <span aria-hidden="true">☼</span><span>Light</span>
        </button>
        <span class="theme-divider" aria-hidden="true"></span>
        <button class="theme-option" id="theme-dark" type="button" aria-pressed="false">
          <span aria-hidden="true">◐</span><span>Dark</span>
        </button>
      </div>
    </header>

    <section class="login-card" aria-labelledby="login-title">
      <div class="card-brand" aria-hidden="true">
        <img class="brand-image brand-image-light" src="/login/brand-light.jpg" alt="">
        <img class="brand-image brand-image-dark" src="/login/brand-dark.jpg" alt="">
      </div>

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
  --bg: #f8faff;
  --surface: rgba(255,255,255,.90);
  --surface-solid: #ffffff;
  --text: #0b0f17;
  --muted: #657084;
  --line: #dce2eb;
  --line-strong: #cbd3df;
  --primary: #0d1118;
  --primary-text: #ffffff;
  --accent: #1672ff;
  --orbital: rgba(99,130,255,.18);
  --glow-a: rgba(36,125,255,.25);
  --glow-b: rgba(126,99,255,.16);
  --shadow: 0 28px 90px rgba(38,53,80,.10);
}

html[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0A0A0A;
  --surface: #141414;
  --surface-solid: #1E1E1E;
  --text: #FFFFFF;
  --muted: #E6E6E6;
  --tertiary: #B3B3B3;
  --disabled: #808080;
  --line: #2A2A2A;
  --line-strong: #2A2A2A;
  --primary: #FFFFFF;
  --primary-text: #0A0A0A;
  --accent: #FFFFFF;
  --hover: #242424;
  --active: #2F2F2F;
  --orbital: rgba(179,179,179,.10);
  --glow-a: transparent;
  --glow-b: transparent;
  --shadow: 0 28px 90px rgba(0,0,0,.48);
}

* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
  margin: 0;
  overflow-x: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}
button, a { font: inherit; }

.ambient {
  position: fixed;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  filter: blur(68px);
  pointer-events: none;
  z-index: 0;
}
.ambient-left { left: -250px; bottom: -290px; background: var(--glow-a); }
.ambient-right { right: -220px; top: 170px; background: var(--glow-b); }

.orbit {
  position: fixed;
  left: 50%;
  top: 52%;
  border: 1px solid var(--orbital);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-7deg);
  pointer-events: none;
  z-index: 0;
}
.orbit::before,
.orbit::after {
  content: "";
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(104,132,255,.55);
}
.orbit::before { left: 13%; top: 9%; }
.orbit::after { right: 8%; bottom: 18%; }
.orbit-one { width: 1060px; height: 430px; }
.orbit-two { width: 900px; height: 340px; transform: translate(-50%, -50%) rotate(9deg); }
.orbit-three { width: 710px; height: 250px; transform: translate(-50%, -50%) rotate(-14deg); }

.shell {
  position: relative;
  z-index: 1;
  width: min(1440px, calc(100% - 64px));
  min-height: 100vh;
  margin: 0 auto;
  display: grid;
  grid-template-rows: 108px 1fr auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand { display: block; width: 278px; height: 70px; text-decoration: none; overflow: hidden; }
.brand-image { width: 100%; height: 100%; object-fit: contain; object-position: left center; }
.brand-image-dark { display: none; }
html[data-theme="dark"] .brand-image-light { display: none; }
html[data-theme="dark"] .brand-image-dark { display: block; }

.theme-switch {
  min-height: 54px;
  display: inline-flex;
  align-items: center;
  padding: 5px 7px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background: var(--surface);
  box-shadow: 0 10px 30px rgba(28,41,65,.07);
  backdrop-filter: blur(18px);
}
.theme-option {
  min-height: 42px;
  padding: 0 17px;
  border: 0;
  border-radius: 22px;
  background: transparent;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 650;
}
.theme-option.is-active { color: var(--accent); background: var(--surface-solid); box-shadow: 0 2px 10px rgba(20,31,50,.06); }
.theme-divider { width: 1px; height: 26px; background: var(--line); }

.login-card {
  align-self: center;
  justify-self: center;
  width: min(100%, 630px);
  padding: 72px 64px 62px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: var(--surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(24px);
  text-align: center;
}
.card-brand { width: 300px; height: 82px; margin: 0 auto 42px; overflow: hidden; }
.card-brand .brand-image { object-position: center; }

h1 {
  margin: 0;
  font-size: clamp(38px, 4vw, 52px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}
.intro {
  margin: 17px 0 40px;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.55;
}
.providers { display: grid; gap: 14px; }
.provider {
  min-height: 68px;
  border: 1px solid var(--line);
  border-radius: 16px;
  display: grid;
  grid-template-columns: 42px 1fr 30px;
  align-items: center;
  gap: 12px;
  padding: 0 22px;
  text-decoration: none;
  text-align: left;
  background: var(--surface-solid);
  color: var(--text);
  font-size: 18px;
  font-weight: 650;
  transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease;
}
.provider:hover { transform: translateY(-1px); border-color: var(--line-strong); box-shadow: 0 8px 24px rgba(28,42,68,.07); }
.provider-primary { background: var(--primary); color: var(--primary-text); border-color: var(--primary); }
.provider-primary:hover { border-color: var(--primary); }
.provider-mark { width: 34px; height: 34px; display: grid; place-items: center; font-weight: 800; }
.google-mark { font-size: 25px; color: #4285f4; }
.github-mark { width: 34px; height: 34px; border-radius: 50%; background: currentColor; color: var(--surface-solid); font-size: 9px; }
.provider-primary .google-mark { background: transparent; }
.microsoft-mark { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; padding: 5px; }
.microsoft-mark i:nth-child(1) { background: #f25022; }
.microsoft-mark i:nth-child(2) { background: #7fba00; }
.microsoft-mark i:nth-child(3) { background: #00a4ef; }
.microsoft-mark i:nth-child(4) { background: #ffb900; }
.microsoft-mark i { width: 11px; height: 11px; display: block; }
.provider-arrow { justify-self: end; font-size: 34px; font-weight: 300; line-height: 1; }
.provider[aria-disabled="true"] { opacity: .42; pointer-events: none; }

.theme-option:focus-visible,
.provider:focus-visible { outline: 3px solid color-mix(in srgb, var(--accent) 38%, transparent); outline-offset: 3px; }

.trust-footer {
  padding: 32px 16px 42px;
  text-align: center;
  color: var(--muted);
}
.trust-line { color: var(--text); font-weight: 600; display: flex; justify-content: center; gap: 9px; align-items: center; }
.trust-shield { color: var(--accent); font-size: 20px; }
.trust-footer p { max-width: 520px; margin: 12px auto 0; line-height: 1.55; }

html[data-theme="dark"] .ambient { display: none; }
html[data-theme="dark"] .orbit::before,
html[data-theme="dark"] .orbit::after { background: #808080; }
html[data-theme="dark"] .theme-switch { box-shadow: none; backdrop-filter: none; }
html[data-theme="dark"] .theme-option { color: #B3B3B3; }
html[data-theme="dark"] .theme-option:hover { background: #242424; color: #E6E6E6; }
html[data-theme="dark"] .theme-option.is-active { color: #FFFFFF; background: #2F2F2F; box-shadow: none; }
html[data-theme="dark"] .login-card { background: #141414; backdrop-filter: none; }
html[data-theme="dark"] .intro { color: #E6E6E6; }
html[data-theme="dark"] .provider:not(.provider-primary) { background: #1E1E1E; color: #FFFFFF; }
html[data-theme="dark"] .provider:not(.provider-primary):hover { background: #242424; border-color: #2A2A2A; box-shadow: none; }
html[data-theme="dark"] .provider:not(.provider-primary):active { background: #2F2F2F; }
html[data-theme="dark"] .provider-primary:hover { background: #E6E6E6; }
html[data-theme="dark"] .provider-primary:active { background: #B3B3B3; border-color: #B3B3B3; }
html[data-theme="dark"] .provider[aria-disabled="true"] { color: #808080; opacity: 1; }
html[data-theme="dark"] .theme-option:focus-visible,
html[data-theme="dark"] .provider:focus-visible { outline: 2px solid #E6E6E6; outline-offset: 3px; }
html[data-theme="dark"] .trust-shield { color: #E6E6E6; }
html[data-theme="dark"] .trust-footer { color: #B3B3B3; }
html[data-theme="dark"] .trust-line { color: #E6E6E6; }

@media (max-width: 760px) {
  .shell { width: min(100% - 24px, 1440px); grid-template-rows: 84px 1fr auto; }
  .brand { width: 170px; height: 52px; }
  .theme-switch { min-height: 44px; }
  .theme-option { min-height: 34px; padding: 0 11px; }
  .theme-option span:last-child { display: none; }
  .login-card { padding: 48px 24px 42px; border-radius: 22px; }
  .card-brand { width: 240px; height: 66px; margin-bottom: 32px; }
  h1 { font-size: 36px; }
  .intro { font-size: 16px; margin-bottom: 30px; }
  .provider { min-height: 62px; font-size: 16px; padding: 0 16px; }
  .orbit { opacity: .55; }
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
function apply(theme){const value=theme==='dark'?'dark':'light';root.dataset.theme=value;const dark=value==='dark';lightButton.classList.toggle('is-active',!dark);darkButton.classList.toggle('is-active',dark);lightButton.setAttribute('aria-pressed',String(!dark));darkButton.setAttribute('aria-pressed',String(dark));const meta=document.querySelector('meta[name=theme-color]');if(meta){meta.setAttribute('content',dark?'#0A0A0A':'#f8faff');}}
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