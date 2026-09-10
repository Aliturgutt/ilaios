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
from urllib.parse import parse_qs, urlsplit

from apps.web_app_runtime.server import (
    AppHTTPServer,
    AppRuntime,
    AppRuntimeConfigurationError,
    RuntimeRequest,
    RuntimeResponse,
)
from apps.web_app_runtime.subscription_ui import render_subscription, subscription_asset

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BRAND_DIR = _REPO_ROOT / "brand" / "assets"
_BRAND_LIGHT = (_BRAND_DIR / "13-ilaios-primary-horizontal-light.jpg").read_bytes()
_BRAND_DARK = (_BRAND_DIR / "02-ilaios-primary-horizontal-dark.jpg").read_bytes()

_LOGIN_HTML_EN = """<!doctype html>
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
    <nav class="language-control" aria-label="Language">
      <a class="language-link" href="/?lang=tr" hreflang="tr">TR</a>
      <a class="language-link is-active" href="/?lang=en" hreflang="en" aria-current="page">EN</a>
    </nav>
    <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Toggle theme" title="Toggle theme">
      <span aria-hidden="true">◐</span>
      <strong>Theme</strong>
    </button>

    <section class="auth" aria-labelledby="login-title">
      <div class="brand-lockup" aria-label="ILAIOS">
        <img class="brand-image brand-image-light" src="/login/brand-light.jpg" alt="ILAIOS">
        <img class="brand-image brand-image-dark" src="/login/brand-dark.jpg" alt="ILAIOS">
      </div>

      <h1 id="login-title">Welcome</h1>
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
      <a href="/subscription?lang=en">Plans and subscription</a>
    </section>
  </main>
  <script src="/login/app.js" defer></script>
</body>
</html>
""".encode("utf-8")

_LOGIN_HTML_TR = (
    _LOGIN_HTML_EN.decode("utf-8")
    .replace('<html lang="en"', '<html lang="tr"', 1)
    .replace("<title>Sign in | ILAIOS</title>", "<title>Giriş yap | ILAIOS</title>", 1)
    .replace('aria-label="Language"', 'aria-label="Dil"', 1)
    .replace(
        '<a class="language-link" href="/?lang=tr" hreflang="tr">TR</a>',
        '<a class="language-link is-active" href="/?lang=tr" hreflang="tr" aria-current="page">TR</a>',
        1,
    )
    .replace(
        '<a class="language-link is-active" href="/?lang=en" hreflang="en" aria-current="page">EN</a>',
        '<a class="language-link" href="/?lang=en" hreflang="en">EN</a>',
        1,
    )
    .replace('aria-label="Toggle theme"', 'aria-label="Temayı değiştir"', 1)
    .replace('title="Toggle theme"', 'title="Temayı değiştir"', 1)
    .replace("<strong>Theme</strong>", "<strong>Tema</strong>", 1)
    .replace("<h1 id=\"login-title\">Welcome</h1>", "<h1 id=\"login-title\">Hoş geldiniz</h1>", 1)
    .replace("Choose an account to continue.", "Devam etmek için bir hesap seçin.", 1)
    .replace("Continue with Google", "Google ile devam et", 1)
    .replace("Continue with Microsoft", "Microsoft ile devam et", 1)
    .replace("Continue with GitHub", "GitHub ile devam et", 1)
    .replace('href="/subscription?lang=en">Plans and subscription',
             'href="/subscription?lang=tr">Planlar ve abonelik', 1)
    .replace(
        "By continuing, you acknowledge the ILAIOS authentication and security controls.",
        "Devam ederek ILAIOS kimlik doğrulama ve güvenlik kontrollerini kabul etmiş olursunuz.",
        1,
    )
).encode("utf-8")

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
.language-control{position:fixed;top:20px;left:22px;display:inline-flex;gap:4px;padding:3px;border:1px solid var(--line);border-radius:10px;background:var(--bg)}
.language-link{height:30px;min-width:34px;display:grid;place-items:center;padding:0 9px;border-radius:7px;color:var(--muted);font-size:12px;font-weight:600;text-decoration:none}
.language-link:hover{color:var(--text);background:var(--button-hover)}
.language-link.is-active{color:var(--text);background:var(--button-active)}
.theme-toggle{position:fixed;top:20px;right:22px;display:inline-flex;align-items:center;gap:7px;min-height:36px;padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:transparent;color:var(--text);font:inherit;cursor:pointer}
.theme-toggle span{color:var(--text);font-size:.95rem}
.theme-toggle strong{font-size:.78rem}
.theme-toggle:hover{background:var(--button-hover);border-color:var(--line-hover)}
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
.language-link:focus-visible,.theme-toggle:focus-visible,.provider:focus-visible{outline:2px solid var(--text);outline-offset:2px}
.notice{max-width:350px;margin:22px auto 0;color:var(--muted);font-size:11px;line-height:1.55}
@media (max-width:560px){.shell{padding:72px 18px 32px}.language-control{top:14px;left:14px}.theme-toggle{top:14px;right:14px}.auth{width:min(100%,360px)}.brand-lockup{width:197.8px;height:66.7px;margin-bottom:24px}h1{font-size:25px}.intro{margin-bottom:24px}.provider{height:48px}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important}}
"""

_LOGIN_JS = b"""(function(){\"use strict\";
const root=document.documentElement;const themeToggle=document.getElementById('theme-toggle');
function storedTheme(){try{return localStorage.getItem('ilaios-theme');}catch(_error){return null;}}
function storeTheme(value){try{localStorage.setItem('ilaios-theme',value);}catch(_error){return;}}
function apply(theme){const value=theme==='dark'?'dark':'light';root.dataset.theme=value;root.style.colorScheme=value;const meta=document.querySelector('meta[name=theme-color]');if(meta){meta.setAttribute('content',value==='dark'?'#0A0A0A':'#FFFFFF');}}
function normalizeBrandBackground(image,dark){if(!image){return;}function run(){if(!image.naturalWidth||!image.naturalHeight){return;}try{const canvas=document.createElement('canvas');const width=image.naturalWidth;const height=image.naturalHeight;canvas.width=width;canvas.height=height;const context=canvas.getContext('2d',{willReadFrequently:true});if(!context){return;}context.drawImage(image,0,0);const frame=context.getImageData(0,0,width,height);const pixels=frame.data;const seen=new Uint8Array(width*height);const queue=new Int32Array(width*height);let head=0;let tail=0;function eligible(position){const offset=position*4;const red=pixels[offset];const green=pixels[offset+1];const blue=pixels[offset+2];return dark?(red<=12&&green<=12&&blue<=16):(red>=248&&green>=248&&blue>=248);}function enqueue(position){if(position<0||position>=width*height||seen[position]||!eligible(position)){return;}seen[position]=1;queue[tail++]=position;}for(let x=0;x<width;x++){enqueue(x);enqueue((height-1)*width+x);}for(let y=0;y<height;y++){enqueue(y*width);enqueue(y*width+width-1);}while(head<tail){const position=queue[head++];const offset=position*4;pixels[offset]=dark?10:255;pixels[offset+1]=dark?10:255;pixels[offset+2]=dark?10:255;pixels[offset+3]=255;const x=position%width;const y=(position/width)|0;if(x>0){enqueue(position-1);}if(x+1<width){enqueue(position+1);}if(y>0){enqueue(position-width);}if(y+1<height){enqueue(position+width);}}context.putImageData(frame,0,0);canvas.className=image.className;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',image.alt||'ILAIOS');image.replaceWith(canvas);}catch(_error){return;}}if(image.complete){run();}else{image.addEventListener('load',run,{once:true});}}
normalizeBrandBackground(document.querySelector('.brand-image-light'),false);normalizeBrandBackground(document.querySelector('.brand-image-dark'),true);
apply(storedTheme()==='dark'?'dark':'light');themeToggle.addEventListener('click',function(){const next=root.dataset.theme==='dark'?'light':'dark';apply(next);storeTheme(next);});
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
        if split.path == "/subscription":
            if method != "GET":
                return self._method_not_allowed("GET")
            query = parse_qs(split.query, keep_blank_values=True)
            if (set(query) - {"lang"}
                    or any(len(value) != 1 for value in query.values())):
                return self._json_error(HTTPStatus.BAD_REQUEST, "unexpected query parameters")
            language = query.get("lang", ["tr"])[0]
            if language not in {"tr", "en"}:
                return self._json_error(HTTPStatus.BAD_REQUEST, "invalid locale")
            return self._asset_response(
                render_subscription(language), "text/html; charset=utf-8",
                csp=("default-src 'none'; script-src 'self'; style-src 'self'; "
                     "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                     "frame-ancestors 'none'; form-action 'none'"),
            )
        if split.path in {"/subscription/styles.css", "/subscription/app.js"}:
            if method != "GET":
                return self._method_not_allowed("GET")
            if split.query:
                return self._json_error(HTTPStatus.BAD_REQUEST, "unexpected query parameters")
            name = split.path.rsplit("/", 1)[1]
            return self._asset_response(
                subscription_asset(name),
                "text/css; charset=utf-8" if name == "styles.css" else "text/javascript; charset=utf-8",
            )
        if split.path == "/":
            if method != "GET":
                return self._method_not_allowed("GET")
            language = "tr"
            if split.query:
                query = parse_qs(split.query, keep_blank_values=True)
                if (
                    set(query) != {"lang"}
                    or len(query["lang"]) != 1
                    or query["lang"][0] not in {"tr", "en"}
                ):
                    return self._json_error(
                        HTTPStatus.BAD_REQUEST, "unexpected query parameters"
                    )
                language = query["lang"][0]
            return self._asset_response(
                _LOGIN_HTML_TR if language == "tr" else _LOGIN_HTML_EN,
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
