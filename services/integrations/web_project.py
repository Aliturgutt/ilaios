"""ILAIOS-owned Next.js/React/TypeScript project materialization for Web Factory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .web_factory import WebsiteSpec


@dataclass(frozen=True, slots=True)
class WebProjectFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class WebProjectArtifact:
    project_id: str
    root_path: str
    digest: str
    files: tuple[WebProjectFile, ...]


def materialize_next_project(
    spec: WebsiteSpec,
    design_strategy: Mapping[str, object],
    output_root: Path,
) -> WebProjectArtifact:
    """Create a deterministic, inspectable Next.js source project for the site."""
    files = _project_files(spec, design_strategy)
    digest = _content_hash(files)
    project_id = f"ilaios-next-{digest[:20]}"
    root = output_root / project_id
    if root.exists():
        _verify_existing(root, files)
    else:
        for relative_path, body in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    evidence = tuple(
        WebProjectFile(path, hashlib.sha256(body).hexdigest(), len(body))
        for path, body in sorted(files.items())
    )
    return WebProjectArtifact(project_id, str(root), digest, evidence)


def _project_files(
    spec: WebsiteSpec,
    design_strategy: Mapping[str, object],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        "package.json": _package_json(spec),
        "tsconfig.json": _tsconfig(),
        "next-env.d.ts": (
            b'/// <reference types="next" />\n'
            b'/// <reference types="next/image-types/global" />\n'
        ),
        "next.config.mjs": (
            b"/** @type {import('next').NextConfig} */\n"
            b"const config = { reactStrictMode: true };\nexport default config;\n"
        ),
        "site.json": json.dumps(
            {"spec": spec.to_dict(), "design_strategy": dict(design_strategy)},
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8"),
        "app/globals.css": _css().encode(),
        "app/layout.tsx": _layout_source(spec).encode(),
        "app/page.tsx": _root_source(spec).encode(),
        "components/PageShell.tsx": _page_shell_source().encode(),
    }
    for locale in spec.locales:
        for page in spec.pages:
            relative = (
                f"app/{locale}/page.tsx"
                if page == "home"
                else f"app/{locale}/{page}/page.tsx"
            )
            files[relative] = _page_source(spec, locale, page).encode()
    return files


def _package_json(spec: WebsiteSpec) -> bytes:
    return json.dumps(
        {
            "name": f"@ilaios/generated-{spec.site_id}",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "build": "next build",
                "start": "next start",
                "typecheck": "tsc --noEmit",
            },
            "dependencies": {
                "next": "16.2.11",
                "react": "19.2.0",
                "react-dom": "19.2.0",
            },
            "devDependencies": {
                "@types/node": "^24.0.0",
                "@types/react": "^19.2.0",
                "@types/react-dom": "^19.2.0",
                "typescript": "^5.9.0",
            },
        },
        sort_keys=True,
        indent=2,
    ).encode()


def _tsconfig() -> bytes:
    return json.dumps(
        {
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": False,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "react-jsx",
                "incremental": True,
                "plugins": [{"name": "next"}],
            },
            "include": [
                "next-env.d.ts",
                "**/*.ts",
                "**/*.tsx",
                ".next/types/**/*.ts",
            ],
            "exclude": ["node_modules"],
        },
        sort_keys=True,
        indent=2,
    ).encode()


def _layout_source(spec: WebsiteSpec) -> str:
    title = json.dumps(spec.business_name, ensure_ascii=False)
    description = json.dumps(
        f"{spec.business_name} — {spec.business_category}", ensure_ascii=False
    )
    locale = json.dumps(spec.locales[0])
    return f'''import type {{ Metadata }} from "next";
import type {{ ReactNode }} from "react";
import "./globals.css";

export const metadata: Metadata = {{ title: {title}, description: {description} }};

export default function RootLayout({{ children }}: Readonly<{{ children: ReactNode }}>) {{
  return <html lang={locale}><body>{{children}}</body></html>;
}}
'''


def _root_source(spec: WebsiteSpec) -> str:
    destination = json.dumps("/" + spec.locales[0])
    return f'''import {{ redirect }} from "next/navigation";

export default function RootPage() {{
  redirect({destination});
}}
'''


def _page_source(spec: WebsiteSpec, locale: str, page: str) -> str:
    props = {
        "locale": locale,
        "businessName": spec.business_name,
        "businessCategory": spec.business_category,
        "audience": spec.audience,
        "pageName": page,
        "pages": list(spec.pages),
        "locales": list(spec.locales),
        "headline": _headline(spec, locale, page),
        "copy": _copy(spec, locale, page),
    }
    import_path = (
        "../../components/PageShell"
        if page == "home"
        else "../../../components/PageShell"
    )
    return f'''import {{ PageShell }} from {json.dumps(import_path)};

const content = {json.dumps(props, ensure_ascii=False, indent=2)} as const;

export default function GeneratedPage() {{
  return <PageShell {{...content}} />;
}}
'''


def _page_shell_source() -> str:
    return '''type Props = {
  locale: string;
  businessName: string;
  businessCategory: string;
  audience: string;
  pageName: string;
  pages: readonly string[];
  locales: readonly string[];
  headline: string;
  copy: string;
};

const labels: Record<string, Record<string, string>> = {
  en: { home: "Home", expertise: "Expertise", about: "About", contact: "Contact", capabilities: "Capabilities", trust: "Trust", menu: "Menu", story: "Story", work: "Work", studio: "Studio", collection: "Collection", craft: "Craft", product: "Product", developers: "Developers", security: "Security", services: "Services", approach: "Approach", care: "Care", solutions: "Solutions", pricing: "Pricing" },
  tr: { home: "Ana sayfa", expertise: "Uzmanlık", about: "Hakkımızda", contact: "İletişim", capabilities: "Yetenekler", trust: "Güven", menu: "Menü", story: "Hikâye", work: "Projeler", studio: "Stüdyo", collection: "Koleksiyon", craft: "Zanaat", product: "Ürün", developers: "Geliştiriciler", security: "Güvenlik", services: "Hizmetler", approach: "Yaklaşım", care: "Bakım", solutions: "Çözümler", pricing: "Fiyatlandırma" },
};

function href(locale: string, page: string) {
  return page === "home" ? `/${locale}` : `/${locale}/${page}`;
}

function ContactForm({ locale }: { locale: string }) {
  return (
    <form className="contact-form" action="#" method="post">
      <label htmlFor="name">{locale === "tr" ? "Ad" : "Name"}</label>
      <input id="name" name="name" autoComplete="name" required />
      <label htmlFor="email">{locale === "tr" ? "E-posta" : "Email"}</label>
      <input id="email" name="email" type="email" autoComplete="email" required />
      <label htmlFor="message">{locale === "tr" ? "Mesaj" : "Message"}</label>
      <textarea id="message" name="message" required />
      <button type="submit">{locale === "tr" ? "Talebi gönder" : "Send request"}</button>
    </form>
  );
}

export function PageShell(props: Props) {
  const t = labels[props.locale] ?? labels.en;
  return (
    <>
      <a className="skip-link" href="#main">{props.locale === "tr" ? "İçeriğe geç" : "Skip to content"}</a>
      <header className="site-header">
        <a className="brand" href={`/${props.locale}`}>{props.businessName}</a>
        <nav aria-label={props.locale === "tr" ? "Ana navigasyon" : "Primary navigation"}>
          {props.pages.map((page) => <a key={page} href={href(props.locale, page)}>{t[page] ?? page}</a>)}
        </nav>
        <div className="languages">
          {props.locales.filter((locale) => locale !== props.locale).map((locale) => (
            <a key={locale} href={`/${locale}`} hrefLang={locale}>{locale.toUpperCase()}</a>
          ))}
        </div>
      </header>
      <main id="main">
        <section className={props.pageName === "home" ? "hero" : "content-block"}>
          <p className="eyebrow">{props.businessCategory}</p>
          <h1>{props.headline}</h1>
          <p className="lede">{props.copy}</p>
          {props.pageName === "home" && <a className="primary-action" href={href(props.locale, "contact")}>{props.locale === "tr" ? "Görüşme başlat" : "Start a conversation"}</a>}
          {props.pageName === "contact" && <ContactForm locale={props.locale} />}
          {props.pageName !== "home" && props.pageName !== "contact" && <div className="evidence-line"><strong>{props.locale === "tr" ? "Odak" : "Built around"}</strong><span>{props.audience}</span></div>}
        </section>
      </main>
      <footer><p>{props.locale === "tr" ? "Netlik, güven ve ölçülebilir aksiyon için tasarlandı." : "Built for clarity, trust, and measurable action."}</p></footer>
    </>
  );
}
'''


def _headline(spec: WebsiteSpec, locale: str, page: str) -> str:
    if page != "home":
        return _label(page, locale)
    if locale == "tr":
        return {
            "law firm": "Belirsizliğe yer bırakmayan kararlar için hukuk danışmanlığı.",
            "security": "Denetime dayanacak şekilde tasarlanmış güvenlik mimarisi.",
            "restaurant": "Kendine ait bir karakteri olan yeme içme deneyimi.",
            "architecture studio": "Amaç, malzeme ve bağlamla şekillenen mekânlar.",
            "furniture": "Oran, malzeme ve kalıcılık üzerine kurulu mobilya.",
            "developer platform": "Karmaşık sistemleri işletmeyi kolaylaştıran altyapı.",
            "financial services": "Sermaye, risk ve uzun vadeli kararlar için netlik.",
            "healthcare": "Net kararlar ve insan odağı etrafında tasarlanmış bakım.",
            "saas": "Karmaşık işi güvenilir bir sisteme dönüştüren yazılım.",
            "professional services": "Uzmanlığı netlik ve güvenle sunan profesyonel hizmet.",
        }[spec.business_category]
    return {
        "law firm": "Counsel for decisions that cannot afford ambiguity.",
        "security": "Security architecture designed to withstand scrutiny.",
        "restaurant": "A dining experience with a point of view.",
        "architecture studio": "Spaces shaped by purpose, material, and context.",
        "furniture": "Furniture with proportion, material, and permanence.",
        "developer platform": "Infrastructure that makes complex systems easier to operate.",
        "financial services": "Clarity for capital, risk, and long-term decisions.",
        "healthcare": "Care designed around clear decisions and human attention.",
        "saas": "Software that turns complex work into a reliable system.",
        "professional services": "Expert work, presented with clarity and conviction.",
    }[spec.business_category]


def _copy(spec: WebsiteSpec, locale: str, page: str) -> str:
    if locale == "tr":
        if page == "home":
            return f"{spec.business_name}, {spec.audience} için güvenilir, erişilebilir ve amaca dönük bir dijital deneyim sunar."
        return f"{spec.business_name} için {_label(page, locale).lower()} sayfası; güven, netlik ve kullanıcı aksiyonu için yapılandırılmıştır."
    if page == "home":
        return f"{spec.business_name} presents a credible, accessible, outcome-oriented experience for {spec.audience}."
    return f"{_label(page, locale)} for {spec.business_name}, structured for trust, clarity, and user action."


def _label(page: str, locale: str) -> str:
    tr = {
        "home": "Ana sayfa",
        "expertise": "Uzmanlık",
        "about": "Hakkımızda",
        "contact": "İletişim",
        "capabilities": "Yetenekler",
        "trust": "Güven",
        "menu": "Menü",
        "story": "Hikâye",
        "work": "Projeler",
        "studio": "Stüdyo",
        "collection": "Koleksiyon",
        "craft": "Zanaat",
        "product": "Ürün",
        "developers": "Geliştiriciler",
        "security": "Güvenlik",
        "services": "Hizmetler",
        "approach": "Yaklaşım",
        "care": "Bakım",
        "solutions": "Çözümler",
        "pricing": "Fiyatlandırma",
    }
    return (
        tr.get(page, page.replace("-", " ").title())
        if locale == "tr"
        else page.replace("-", " ").title()
    )


def _css() -> str:
    return """
:root{--ink:#101828;--muted:#475467;--line:#d0d5dd;--accent:#0b5fff;--max:1180px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:#fff;line-height:1.55}a{color:inherit}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.skip-link{position:absolute;left:-999px;top:0}.skip-link:focus{left:1rem;top:1rem;background:#fff;padding:.75rem;z-index:10}.site-header{max-width:var(--max);margin:auto;padding:1.2rem 1.5rem;display:grid;grid-template-columns:auto 1fr auto;gap:clamp(1.25rem,3vw,3rem);align-items:center;border-bottom:1px solid var(--line)}.brand{font-weight:800;text-decoration:none}nav{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap}nav a,.languages a{display:inline-flex;align-items:center;min-height:40px;text-decoration:none}main{max-width:var(--max);margin:auto;padding:clamp(2rem,6vw,6rem) 1.5rem}.hero{min-height:58vh;display:grid;align-content:center}.hero h1,.content-block h1{font-size:clamp(2.6rem,7vw,6rem);line-height:1;letter-spacing:-.05em;max-width:13ch;margin:.4rem 0 1.4rem}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.78rem;font-weight:700;color:var(--muted)}.lede{font-size:clamp(1.05rem,1.8vw,1.35rem);max-width:60ch}.primary-action{display:inline-flex;align-items:center;min-height:44px;width:max-content;margin-top:1.5rem;background:var(--ink);color:#fff;padding:.75rem 1rem;text-decoration:none}.content-block{max-width:850px}.evidence-line{display:grid;grid-template-columns:140px 1fr;gap:1rem;border-top:1px solid var(--line);padding-top:1rem;margin-top:3rem}.contact-form{display:grid;gap:.65rem;margin-top:2rem;max-width:620px}.contact-form input,.contact-form textarea{font:inherit;padding:.8rem;border:1px solid var(--line)}.contact-form textarea{min-height:150px}.contact-form button{font:inherit;min-height:44px;padding:.75rem 1rem;border:0;background:var(--ink);color:#fff;width:max-content}footer{max-width:var(--max);margin:3rem auto 0;padding:2rem 1.5rem;border-top:1px solid var(--line);color:var(--muted)}@media(max-width:768px){.site-header{grid-template-columns:1fr;align-items:start}nav{justify-content:flex-start}.evidence-line{grid-template-columns:1fr}.hero h1,.content-block h1{font-size:clamp(2.5rem,11vw,4.7rem)}}@media(max-width:430px){main{padding-top:2.25rem}.site-header{padding:1rem}nav{display:grid;grid-template-columns:1fr 1fr;gap:.4rem}.contact-form button{width:100%}}@media(max-width:360px){nav{grid-template-columns:1fr}}@media(max-width:320px){body{font-size:15px}main{padding-left:1rem;padding-right:1rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
""".strip()


def _content_hash(content: Mapping[str, bytes]) -> str:
    material = b"".join(
        path.encode() + b"\0" + body + b"\0"
        for path, body in sorted(content.items())
    )
    return hashlib.sha256(material).hexdigest()


def _verify_existing(root: Path, expected: Mapping[str, bytes]) -> None:
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if actual != set(expected):
        raise ValueError("generated Next.js project file set was tampered")
    for relative_path, body in expected.items():
        if (root / relative_path).read_bytes() != body:
            raise ValueError("generated Next.js project content was tampered")
