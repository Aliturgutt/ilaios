"""Production login surface for app.ilaios.com.

This module adds only the public login UI and delegates all identity, session,
OAuth, Li, and health behavior to the existing canonical AppRuntime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from urllib.parse import urlsplit

from apps.web_app_runtime.server import (
    AppHTTPServer,
    AppRuntime,
    AppRuntimeConfigurationError,
    RuntimeRequest,
    RuntimeResponse,
)

_LOGIN_HTML = """<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="theme-color" content="#f7f7f5">
  <title>Sign in | ILAIOS</title>
  <link rel="stylesheet" href="/login/styles.css">
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="ILAIOS home">
        <span class="brand-mark" aria-hidden="true">I</span>
        <span>ILAIOS</span>
      </a>
      <button class="theme-toggle" id="theme-toggle" type="button" aria-pressed="false" aria-label="Switch to dark mode">
        <span class="theme-icon" aria-hidden="true">◐</span>
        <span id="theme-label">Dark</span>
      </button>
    </header>

    <section class="login-card" aria-labelledby="login-title">
      <div class="eyebrow">ILAIOS account</div>
      <h1 id="login-title">Sign in to continue</h1>
      <p class="intro">Use your existing account to access ILAIOS.</p>

      <div class="providers" id="providers" aria-live="polite">
        <a class="provider provider-primary" data-provider="google" href="/auth/google/start">
          <span class="provider-badge" aria-hidden="true">G</span>
          <span>Continue with Google</span>
        </a>
        <a class="provider" data-provider="microsoft" href="/auth/microsoft/start">
          <span class="provider-badge microsoft-badge" aria-hidden="true">M</span>
          <span>Continue with Microsoft</span>
        </a>
        <a class="provider" data-provider="github" href="/auth/github/start">
          <span class="provider-badge github-badge" aria-hidden="true">GH</span>
          <span>Continue with GitHub</span>
        </a>
      </div>

      <p class="notice">Account linking will be completed after the Desktop experience is finalized.</p>
      <p class="legal">By continuing, you acknowledge the ILAIOS authentication flow and security controls.</p>
    </section>

    <footer>Secure sign-in · app.ilaios.com</footer>
  </main>
  <script src="/login/app.js" defer></script>
</body>
</html>
""".encode("utf-8")

_LOGIN_CSS = b""":root {
  color-scheme: light;
  --bg: #f7f7f5;
  --surface: #ffffff;
  --surface-subtle: #f1f1ef;
  --text: #171717;
  --muted: #6c6c68;
  --line: #deded9;
  --line-strong: #c9c9c2;
  --button: #191919;
  --button-text: #ffffff;
  --focus: #5b66f6;
  --shadow: 0 22px 70px rgba(20, 20, 18, 0.08);
}

html[data-theme="dark"] {
  color-scheme: dark;
  --bg: #111210;
  --surface: #181917;
  --surface-subtle: #20211f;
  --text: #f5f5f1;
  --muted: #a6a69f;
  --line: #30312d;
  --line-strong: #44453f;
  --button: #f5f5f1;
  --button-text: #161714;
  --focus: #8f98ff;
  --shadow: 0 22px 70px rgba(0, 0, 0, 0.28);
}

* { box-sizing: border-box; }

html, body { min-height: 100%; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}

a { color: inherit; }

button, a { font: inherit; }

.shell {
  width: min(1160px, calc(100% - 40px));
  min-height: 100vh;
  margin: 0 auto;
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.topbar {
  height: 88px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: inline-flex;
  gap: 11px;
  align-items: center;
  text-decoration: none;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: var(--text);
  color: var(--bg);
  font-size: 14px;
  font-weight: 800;
}

.theme-toggle {
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.theme-toggle:hover { border-color: var(--line-strong); }

.theme-toggle:focus-visible,
.provider:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--focus) 42%, transparent);
  outline-offset: 3px;
}

.login-card {
  align-self: center;
  justify-self: center;
  width: min(100%, 430px);
  padding: 42px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.eyebrow {
  color: var(--muted);
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 12px 0 9px;
  font-size: clamp(30px, 5vw, 38px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.intro {
  margin: 0 0 28px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.55;
}

.providers { display: grid; gap: 11px; }

.provider {
  min-height: 52px;
  border: 1px solid var(--line);
  border-radius: 14px;
  display: grid;
  grid-template-columns: 30px 1fr 30px;
  align-items: center;
  padding: 0 13px;
  text-decoration: none;
  background: var(--surface);
  font-weight: 650;
  transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
}

.provider::after {
  content: "\2192";
  color: var(--muted);
  justify-self: end;
}

.provider:hover {
  transform: translateY(-1px);
  border-color: var(--line-strong);
  background: var(--surface-subtle);
}

.provider-primary {
  background: var(--button);
  color: var(--button-text);
  border-color: var(--button);
}

.provider-primary:hover {
  background: var(--button);
  border-color: var(--button);
}

.provider-primary::after { color: currentColor; opacity: 0.72; }

.provider-badge {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  border: 1px solid currentColor;
  font-size: 12px;
  font-weight: 800;
}

.microsoft-badge { font-size: 11px; }
.github-badge { font-size: 9px; }

.provider[aria-disabled="true"] {
  opacity: 0.45;
  pointer-events: none;
}

.notice {
  margin: 22px 0 0;
  padding: 13px 14px;
  border-radius: 12px;
  background: var(--surface-subtle);
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.48;
}

.legal {
  margin: 16px 3px 0;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.5;
}

footer {
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 560px) {
  .shell { width: min(100% - 24px, 1160px); }
  .topbar { height: 72px; }
  .login-card { padding: 30px 22px; border-radius: 20px; }
  .theme-toggle { padding: 0 11px; }
  #theme-label { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}
"""

_LOGIN_JS = b"""(function(){\"use strict\";
const root=document.documentElement;
const toggle=document.getElementById('theme-toggle');
const label=document.getElementById('theme-label');
function storedTheme(){try{return localStorage.getItem('ilaios-theme');}catch(_error){return null;}}
function storeTheme(value){try{localStorage.setItem('ilaios-theme',value);}catch(_error){return;}}
function apply(theme){const value=theme==='dark'?'dark':'light';root.dataset.theme=value;const dark=value==='dark';toggle.setAttribute('aria-pressed',String(dark));toggle.setAttribute('aria-label',dark?'Switch to light mode':'Switch to dark mode');label.textContent=dark?'Light':'Dark';const meta=document.querySelector('meta[name=theme-color]');if(meta){meta.setAttribute('content',dark?'#111210':'#f7f7f5');}}
apply(storedTheme()==='dark'?'dark':'light');
toggle.addEventListener('click',function(){const next=root.dataset.theme==='dark'?'light':'dark';apply(next);storeTheme(next);});
fetch('/auth/providers',{credentials:'same-origin',cache:'no-store'}).then(function(response){if(!response.ok){return null;}return response.json();}).then(function(payload){if(!payload||!Array.isArray(payload.providers)){return;}const available=new Set(payload.providers);for(const link of document.querySelectorAll('[data-provider]')){const provider=link.getAttribute('data-provider');if(!available.has(provider)){link.setAttribute('aria-disabled','true');link.setAttribute('tabindex','-1');link.removeAttribute('href');}}}).catch(function(){return;});
})();
"""


class LoginAppRuntime(AppRuntime):
    """Add a bounded public login surface while preserving canonical auth runtime."""

    def dispatch(
        self,
        request: RuntimeRequest,
        *,
        now=None,  # type: ignore[no-untyped-def]
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
                    "connect-src 'self'; img-src 'none'; base-uri 'none'; "
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
            return self._asset_response(
                _LOGIN_JS, "text/javascript; charset=utf-8"
            )
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
