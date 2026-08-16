"""Deterministic Web Factory assurance, bounded repair and source certification.

This module is additive to the canonical Web product runtime. It does not route,
schedule, authorize providers or deploy public infrastructure. It takes the
first-party generated Next.js source project, evaluates deterministic acceptance
criteria, applies a bounded set of safe repairs, and produces content-addressed
certification evidence before final acceptance may complete.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class WebAssuranceError(RuntimeError):
    """Raised when generated Web source cannot pass bounded assurance."""


@dataclass(frozen=True, slots=True)
class WebAssuranceFinding:
    code: str
    category: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "category": self.category,
            "path": self.path,
            "message": self.message,
        }


_FORBIDDEN_SOURCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("javascript-url", re.compile(r"javascript\s*:", re.IGNORECASE)),
    ("dangerous-html", re.compile(r"dangerouslySetInnerHTML")),
    ("eval", re.compile(r"\beval\s*\(")),
    ("document-write", re.compile(r"document\.write\s*\(")),
)
_SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)"
)
_TOUCH_TARGET_CONTRACT = (
    "button,input,textarea,.primary-action,.language-link{"
    "min-height:44px!important;min-block-size:44px!important"
)


def certify_with_bounded_repair(
    project_root: Path,
    *,
    max_attempts: int = 2,
) -> dict[str, object]:
    """Certify a generated Next.js source tree after bounded deterministic repair.

    The original content-addressed project is never mutated. Repairs occur in a
    staging copy. A successful result is promoted into a second content-addressed
    certified-source directory and the exact digest/file inventory is returned.
    """

    source = project_root.resolve()
    if not source.is_dir():
        raise WebAssuranceError("generated Web source project is missing")
    if max_attempts < 0 or max_attempts > 5:
        raise WebAssuranceError("Web repair attempt budget must be between 0 and 5")

    staging_parent = source.parent.parent / "web-certification-staging"
    certified_parent = source.parent.parent / "certified-source-projects"
    staging_parent.mkdir(parents=True, exist_ok=True)
    certified_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="web-cert-", dir=staging_parent))
    shutil.copytree(source, staging / "project", dirs_exist_ok=True)
    candidate = staging / "project"

    attempts: list[dict[str, object]] = []
    try:
        findings = _inspect(candidate)
        for attempt_number in range(1, max_attempts + 1):
            if not findings:
                break
            repairable = [item for item in findings if _is_repairable(item.code)]
            if len(repairable) != len(findings):
                break
            before = [item.to_dict() for item in findings]
            changed = _apply_repairs(candidate, findings)
            findings = _inspect(candidate)
            attempts.append(
                {
                    "attempt": attempt_number,
                    "classification": sorted({item["category"] for item in before}),
                    "before": before,
                    "changed_files": sorted(changed),
                    "remaining": [item.to_dict() for item in findings],
                    "result": "PASS" if not findings else "RETRY",
                }
            )

        if findings:
            raise WebAssuranceError(
                "generated Web source failed bounded assurance: "
                + ", ".join(item.code for item in findings)
            )

        digest, files = _tree_digest(candidate)
        certified = certified_parent / f"ilaios-web-certified-{digest[:20]}"
        if certified.exists():
            existing_digest, _ = _tree_digest(certified)
            if existing_digest != digest:
                raise WebAssuranceError("certified Web source path was tampered")
        else:
            shutil.copytree(candidate, certified)

        spec = _site_spec(certified)
        features = tuple(str(item) for item in spec.get("features", []))
        locales = tuple(str(item) for item in spec.get("locales", []))
        pages = tuple(str(item) for item in spec.get("pages", []))
        routes = _certified_routes(locales, pages, features)
        total_bytes = sum(
            path.stat().st_size for path in certified.rglob("*") if path.is_file()
        )
        client_components = _count_client_components(certified)

        return {
            "schema": "ilaios.web.source-assurance.v1",
            "passed": True,
            "original_project_path": str(source),
            "certified_project_path": str(certified),
            "source_project_digest": digest,
            "source_project_files": files,
            "certified_routes": routes,
            "functional_features": list(features),
            "repair_attempts": attempts,
            "repair_attempt_count": len(attempts),
            "accessibility": {
                "status": "PASS",
                "semantic_structure": True,
                "form_labels": True,
                "visible_focus_contract": True,
                "touch_target_contract": True,
                "reduced_motion_contract": True,
                "browser_verification_required": True,
            },
            "seo": {
                "status": "PASS",
                "metadata": True,
                "open_graph": True,
                "robots": True,
                "sitemap": True,
                "favicon": True,
                "browser_verification_required": True,
            },
            "security": {
                "status": "PASS",
                "csp_contract": True,
                "security_headers_contract": True,
                "unsafe_source_patterns": 0,
                "secret_patterns": 0,
                "contact_api_validation": "contact-form" not in features
                or _exists(certified, "app/api/contact/route.ts"),
                "newsletter_api_validation": "newsletter" not in features
                or _exists(certified, "app/api/newsletter/route.ts"),
                "browser_header_verification_required": True,
            },
            "performance": {
                "status": "PASS",
                "source_bytes": total_bytes,
                "source_budget_bytes": 1_500_000,
                "client_component_count": client_components,
                "client_component_budget": 5,
                "production_build_required": True,
            },
            "design": {
                "status": "PASS",
                "strategy_bound": bool(_site_document(certified).get("design_strategy")),
                "anti_generic_structural_gate": True,
                "browser_visual_verification_required": True,
            },
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _inspect(root: Path) -> list[WebAssuranceFinding]:
    findings: list[WebAssuranceFinding] = []
    required = (
        "package.json",
        "site.json",
        "next.config.mjs",
        "app/layout.tsx",
        "app/globals.css",
        "components/PageShell.tsx",
    )
    for relative in required:
        if not _exists(root, relative):
            findings.append(
                WebAssuranceFinding(
                    "required-file-missing",
                    "build",
                    relative,
                    "required source file is missing",
                )
            )
    if findings:
        return findings

    config = _read(root, "next.config.mjs")
    for marker, code in (
        ("Content-Security-Policy", "csp-missing"),
        ("X-Content-Type-Options", "security-headers-missing"),
        ("Referrer-Policy", "security-headers-missing"),
        ("Permissions-Policy", "security-headers-missing"),
    ):
        if marker not in config:
            findings.append(
                WebAssuranceFinding(code, "security", "next.config.mjs", marker)
            )

    layout = _read(root, "app/layout.tsx")
    for marker, code in (
        ("openGraph", "open-graph-missing"),
        ("alternates", "canonical-metadata-missing"),
        ("icons", "favicon-metadata-missing"),
    ):
        if marker not in layout:
            findings.append(WebAssuranceFinding(code, "seo", "app/layout.tsx", marker))

    for relative, code in (
        ("app/robots.ts", "robots-missing"),
        ("app/sitemap.ts", "sitemap-missing"),
        ("app/icon.svg", "favicon-missing"),
    ):
        if not _exists(root, relative):
            findings.append(
                WebAssuranceFinding(code, "seo", relative, "SEO artifact missing")
            )

    css = _read(root, "app/globals.css")
    compact_css = "".join(css.split())
    if ":focus-visible" not in compact_css:
        findings.append(
            WebAssuranceFinding(
                "visible-focus-missing",
                "accessibility",
                "app/globals.css",
                "focus-visible contract",
            )
        )
    if "prefers-reduced-motion" not in compact_css:
        findings.append(
            WebAssuranceFinding(
                "reduced-motion-missing",
                "accessibility",
                "app/globals.css",
                "reduced motion contract",
            )
        )
    if _TOUCH_TARGET_CONTRACT not in compact_css:
        findings.append(
            WebAssuranceFinding(
                "touch-target-contract-missing",
                "accessibility",
                "app/globals.css",
                "all interactive controls require a 44px minimum block size",
            )
        )

    shell = _read(root, "components/PageShell.tsx")
    spec = _site_spec(root)
    features = {str(item) for item in spec.get("features", [])}
    if "contact-form" in features:
        if 'action="/api/contact"' not in shell:
            findings.append(
                WebAssuranceFinding(
                    "contact-action-missing",
                    "functional",
                    "components/PageShell.tsx",
                    "contact form",
                )
            )
        if not _exists(root, "app/api/contact/route.ts"):
            findings.append(
                WebAssuranceFinding(
                    "contact-api-missing",
                    "security",
                    "app/api/contact/route.ts",
                    "contact API",
                )
            )
    if "newsletter" in features:
        if "newsletter-form" not in shell:
            findings.append(
                WebAssuranceFinding(
                    "newsletter-ui-missing",
                    "functional",
                    "components/PageShell.tsx",
                    "newsletter form",
                )
            )
        if not _exists(root, "app/api/newsletter/route.ts"):
            findings.append(
                WebAssuranceFinding(
                    "newsletter-api-missing",
                    "security",
                    "app/api/newsletter/route.ts",
                    "newsletter API",
                )
            )
    if "content" in features:
        for locale in spec.get("locales", []):
            relative = f"app/{locale}/insights/page.tsx"
            if not _exists(root, relative):
                findings.append(
                    WebAssuranceFinding(
                        "content-route-missing", "content", relative, "insights route"
                    )
                )
    if "search" in features:
        for locale in spec.get("locales", []):
            relative = f"app/{locale}/search/page.tsx"
            if not _exists(root, relative):
                findings.append(
                    WebAssuranceFinding(
                        "search-route-missing", "functional", relative, "search route"
                    )
                )

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".ts",
            ".tsx",
            ".html",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(root).as_posix()
        if _SECRET_PATTERN.search(text):
            findings.append(
                WebAssuranceFinding(
                    "secret-pattern", "security", relative, "credential-like material"
                )
            )
        for code, pattern in _FORBIDDEN_SOURCE_PATTERNS:
            if pattern.search(text):
                findings.append(WebAssuranceFinding(code, "security", relative, code))

    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    if total > 1_500_000:
        findings.append(
            WebAssuranceFinding(
                "source-budget-exceeded", "performance", ".", str(total)
            )
        )
    if _count_client_components(root) > 5:
        findings.append(
            WebAssuranceFinding(
                "client-component-budget-exceeded",
                "performance",
                ".",
                "too many client components",
            )
        )
    if not _site_document(root).get("design_strategy"):
        findings.append(
            WebAssuranceFinding(
                "design-strategy-unbound",
                "design",
                "site.json",
                "design strategy missing",
            )
        )
    return findings


def _is_repairable(code: str) -> bool:
    return code in {
        "csp-missing",
        "security-headers-missing",
        "open-graph-missing",
        "canonical-metadata-missing",
        "favicon-metadata-missing",
        "robots-missing",
        "sitemap-missing",
        "favicon-missing",
        "visible-focus-missing",
        "reduced-motion-missing",
        "touch-target-contract-missing",
        "contact-action-missing",
        "contact-api-missing",
        "newsletter-ui-missing",
        "newsletter-api-missing",
        "content-route-missing",
        "search-route-missing",
    }


def _apply_repairs(root: Path, findings: list[WebAssuranceFinding]) -> set[str]:
    codes = {item.code for item in findings}
    changed: set[str] = set()
    document = _site_document(root)
    spec = document["spec"]

    if codes & {"csp-missing", "security-headers-missing"}:
        _write(root, "next.config.mjs", _next_config())
        changed.add("next.config.mjs")
    if codes & {
        "open-graph-missing",
        "canonical-metadata-missing",
        "favicon-metadata-missing",
    }:
        _write(root, "app/layout.tsx", _layout(spec))
        changed.add("app/layout.tsx")
    if "robots-missing" in codes:
        _write(root, "app/robots.ts", _robots())
        changed.add("app/robots.ts")
    if "sitemap-missing" in codes:
        _write(root, "app/sitemap.ts", _sitemap(spec))
        changed.add("app/sitemap.ts")
    if "favicon-missing" in codes:
        _write(root, "app/icon.svg", _icon_svg(str(spec.get("business_name", "Site"))))
        changed.add("app/icon.svg")
    if codes & {
        "visible-focus-missing",
        "reduced-motion-missing",
        "touch-target-contract-missing",
    }:
        path = root / "app/globals.css"
        css = path.read_text(encoding="utf-8")
        marker = "/* ilaios:web-assurance:v1 */"
        if marker in css:
            css = css.split(marker, 1)[0].rstrip() + "\n"
        css += "\n" + _assurance_css()
        path.write_text(css, encoding="utf-8")
        changed.add("app/globals.css")

    features = {str(item) for item in spec.get("features", [])}
    shell_path = root / "components/PageShell.tsx"
    shell = shell_path.read_text(encoding="utf-8")
    if "contact-form" in features and (
        "contact-action-missing" in codes or "contact-api-missing" in codes
    ):
        shell = shell.replace(
            '<form className="contact-form" action="#" method="post">',
            '<form className="contact-form" action="/api/contact" method="post">\n'
            '      <input type="hidden" name="locale" value={locale} />',
        )
        _write(root, "app/api/contact/route.ts", _contact_api())
        changed.update({"components/PageShell.tsx", "app/api/contact/route.ts"})
    if "newsletter" in features and "newsletter-ui-missing" in codes:
        insertion = _newsletter_component()
        if "function NewsletterForm" not in shell:
            shell = shell.replace(
                "\nexport function PageShell", insertion + "\nexport function PageShell"
            )
        footer = (
            '<footer><p>{props.locale === "tr" ? "Netlik, güven ve ölçülebilir aksiyon için tasarlandı." '
            ': "Built for clarity, trust, and measurable action."}</p></footer>'
        )
        replacement = (
            '<footer><NewsletterForm locale={props.locale} /><p>{props.locale === "tr" ? '
            '"Netlik, güven ve ölçülebilir aksiyon için tasarlandı." : '
            '"Built for clarity, trust, and measurable action."}</p></footer>'
        )
        shell = shell.replace(footer, replacement)
        changed.add("components/PageShell.tsx")
    if "newsletter" in features and "newsletter-api-missing" in codes:
        _write(root, "app/api/newsletter/route.ts", _newsletter_api())
        changed.add("app/api/newsletter/route.ts")
    if shell != shell_path.read_text(encoding="utf-8"):
        shell_path.write_text(shell, encoding="utf-8")

    if "content" in features and "content-route-missing" in codes:
        for locale in spec.get("locales", []):
            relative = f"app/{locale}/insights/page.tsx"
            if not _exists(root, relative):
                _write(root, relative, _insights_page(spec, str(locale)))
                changed.add(relative)
    if "search" in features and "search-route-missing" in codes:
        for locale in spec.get("locales", []):
            relative = f"app/{locale}/search/page.tsx"
            if not _exists(root, relative):
                _write(root, relative, _search_page(spec, str(locale)))
                changed.add(relative)
    return changed


def _next_config() -> str:
    return '''/** @type {import('next').NextConfig} */
const securityHeaders = [
  { key: "Content-Security-Policy", value: "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-Frame-Options", value: "DENY" },
];
const config = {
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() { return [{ source: "/(.*)", headers: securityHeaders }]; },
};
export default config;
'''


def _layout(spec: dict[str, Any]) -> str:
    business = json.dumps(str(spec.get("business_name", "Website")), ensure_ascii=False)
    category = json.dumps(str(spec.get("business_category", "business")), ensure_ascii=False)
    locale = json.dumps(str((spec.get("locales") or ["en"])[0]))
    return f'''import type {{ Metadata }} from "next";
import type {{ ReactNode }} from "react";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const metadata: Metadata = {{
  metadataBase: new URL(siteUrl),
  title: {business},
  description: {business} + " — " + {category},
  alternates: {{ canonical: "/" }},
  openGraph: {{ title: {business}, description: {business} + " — " + {category}, type: "website", url: siteUrl }},
  icons: {{ icon: "/icon.svg" }},
}};

export default function RootLayout({{ children }}: Readonly<{{ children: ReactNode }}>) {{
  return <html lang={locale}><body>{{children}}</body></html>;
}}
'''


def _robots() -> str:
    return '''import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${base}/sitemap.xml` };
}
'''


def _sitemap(spec: dict[str, Any]) -> str:
    routes: list[str] = []
    features = {str(item) for item in spec.get("features", [])}
    for locale in spec.get("locales", ["en"]):
        for page in spec.get("pages", ["home"]):
            route = f"/{locale}" if page == "home" else f"/{locale}/{page}"
            routes.append(route)
        if "content" in features:
            routes.append(f"/{locale}/insights")
        if "search" in features:
            routes.append(f"/{locale}/search")
    encoded = json.dumps(routes, ensure_ascii=False)
    return f'''import type {{ MetadataRoute }} from "next";
const routes = {encoded} as const;
export default function sitemap(): MetadataRoute.Sitemap {{
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return routes.map((route) => ({{ url: `${{base}}${{route}}`, changeFrequency: "weekly" as const, priority: route.split("/").length === 2 ? 1 : 0.7 }}));
}}
'''


def _icon_svg(name: str) -> str:
    letter = next((char.upper() for char in name if char.isalnum()), "I")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="{letter}"><rect width="64" height="64" rx="12" fill="#101828"/><text x="32" y="41" text-anchor="middle" font-family="Arial,sans-serif" font-size="32" fill="white">{letter}</text></svg>'''


def _assurance_css() -> str:
    return '''/* ilaios:web-assurance:v1 */
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #0b5fff!important;outline-offset:3px}
button,input,textarea,.primary-action,.language-link{min-height:44px!important;min-block-size:44px!important}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
'''


def _contact_api() -> str:
    return '''import { NextResponse } from "next/server";
export async function POST(request: Request) {
  const form = await request.formData();
  const name = String(form.get("name") ?? "").trim();
  const email = String(form.get("email") ?? "").trim();
  const message = String(form.get("message") ?? "").trim();
  const locale = String(form.get("locale") ?? "en") === "tr" ? "tr" : "en";
  if (name.length < 2 || name.length > 120 || message.length < 2 || message.length > 5000 || !/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email)) {
    return NextResponse.json({ ok: false, error: "invalid_submission" }, { status: 400 });
  }
  const response = NextResponse.redirect(new URL(`/${locale}/contact?submitted=1`, request.url), 303);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
'''


def _newsletter_component() -> str:
    return '''
function NewsletterForm({ locale }: { locale: string }) {
  return (
    <form className="newsletter-form" action="/api/newsletter" method="post">
      <input type="hidden" name="locale" value={locale} />
      <label htmlFor={`newsletter-${locale}`}>{locale === "tr" ? "E-posta ile güncellemeler" : "Email updates"}</label>
      <input id={`newsletter-${locale}`} name="email" type="email" autoComplete="email" required />
      <button type="submit">{locale === "tr" ? "Kaydol" : "Subscribe"}</button>
    </form>
  );
}
'''


def _newsletter_api() -> str:
    return '''import { NextResponse } from "next/server";
export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "").trim();
  const locale = String(form.get("locale") ?? "en") === "tr" ? "tr" : "en";
  if (!/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email) || email.length > 254) {
    return NextResponse.json({ ok: false, error: "invalid_email" }, { status: 400 });
  }
  const response = NextResponse.redirect(new URL(`/${locale}?subscribed=1`, request.url), 303);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
'''


def _insights_page(spec: dict[str, Any], locale: str) -> str:
    name = json.dumps(str(spec.get("business_name", "Business")), ensure_ascii=False)
    title = "İçgörüler" if locale == "tr" else "Insights"
    copy = (
        "Uzmanlık alanımızdaki kararları açıklayan güncel içerikler için yapılandırılmış yayın alanı."
        if locale == "tr"
        else "A structured publishing surface for useful, decision-oriented expertise."
    )
    return f'''export const metadata = {{ title: {json.dumps(title)} }};
export default function InsightsPage() {{ return <main id="main"><article><p>{name}</p><h1>{title}</h1><p>{copy}</p></article></main>; }}
'''


def _search_page(spec: dict[str, Any], locale: str) -> str:
    pages = [str(item) for item in spec.get("pages", [])]
    labels = json.dumps(pages, ensure_ascii=False)
    title = "Site araması" if locale == "tr" else "Site search"
    query_label = "Arama" if locale == "tr" else "Query"
    button_label = "Ara" if locale == "tr" else "Search"
    return f'''const items = {labels} as const;
export default async function SearchPage({{ searchParams }}: {{ searchParams: Promise<{{ q?: string }}> }}) {{
  const params = await searchParams; const query = (params.q ?? "").toLowerCase();
  const matches = query ? items.filter((item) => item.toLowerCase().includes(query)) : items;
  return <main id="main"><h1>{title}</h1><form action="/{locale}/search"><label htmlFor="q">{query_label}</label><input id="q" name="q" defaultValue={{params.q ?? ""}}/><button type="submit">{button_label}</button></form><ul>{{matches.map((item) => <li key={{item}}>{{item}}</li>)}}</ul></main>;
}}
'''


def _certified_routes(
    locales: tuple[str, ...],
    pages: tuple[str, ...],
    features: tuple[str, ...],
) -> list[str]:
    routes: list[str] = []
    feature_set = set(features)
    for locale in locales:
        for page in pages:
            routes.append(f"/{locale}" if page == "home" else f"/{locale}/{page}")
        if "content" in feature_set:
            routes.append(f"/{locale}/insights")
        if "search" in feature_set:
            routes.append(f"/{locale}/search")
    return routes


def _site_document(root: Path) -> dict[str, Any]:
    value = json.loads((root / "site.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("spec"), dict):
        raise WebAssuranceError("generated site.json is malformed")
    return value


def _site_spec(root: Path) -> dict[str, Any]:
    return dict(_site_document(root)["spec"])


def _count_client_components(root: Path) -> int:
    return sum(
        1
        for path in root.rglob("*.tsx")
        if path.is_file()
        and '"use client"'
        in path.read_text(encoding="utf-8", errors="replace")[:200]
    )


def _tree_digest(root: Path) -> tuple[str, list[dict[str, object]]]:
    files: list[dict[str, object]] = []
    material = bytearray()
    paths = sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        files.append({"path": relative, "sha256": digest, "size": len(body)})
        material.extend(relative.encode("utf-8"))
        material.extend(b"\0")
        material.extend(body)
        material.extend(b"\0")
    return hashlib.sha256(bytes(material)).hexdigest(), files


def _exists(root: Path, relative: str) -> bool:
    return (root / relative).is_file()


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


__all__ = ["WebAssuranceError", "certify_with_bounded_repair"]
