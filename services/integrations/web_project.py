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
        "components/MotionRuntime.tsx": _motion_runtime_source().encode(),
    }
    for locale in spec.locales:
        for page in spec.pages:
            relative = (
                f"app/{locale}/page.tsx"
                if page == "home"
                else f"app/{locale}/{page}/page.tsx"
            )
            files[relative] = _page_source(
                spec, locale, page, design_strategy
            ).encode()
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


def _page_source(
    spec: WebsiteSpec,
    locale: str,
    page: str,
    design_strategy: Mapping[str, object],
) -> str:
    primary = str(design_strategy.get("primary_composition", "editorial-split"))
    secondary_raw = design_strategy.get("secondary_compositions", ())
    secondary = (
        [str(item) for item in secondary_raw]
        if isinstance(secondary_raw, (tuple, list))
        else []
    )
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
        "primaryComposition": primary,
        "secondaryCompositions": secondary,
        "trustRequirement": spec.trust_requirement,
        "informationDensity": spec.information_density,
        "motionIntensity": str(design_strategy.get("motion_intensity", "restrained")),
        "interactionDensity": str(design_strategy.get("interaction_density", "moderate")),
        "scrollBehavior": str(design_strategy.get("scroll_behavior", "section-linked")),
        "showcaseBehavior": str(design_strategy.get("showcase_behavior", "contextual-interactive")),
        "motionAccessibility": str(design_strategy.get("motion_accessibility", "reduced-motion-static-equivalent")),
        "hasNewsletter": "newsletter" in spec.features,
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
    return '''import { MotionRuntime } from "./MotionRuntime";

type Props = {
  locale: string;
  businessName: string;
  businessCategory: string;
  audience: string;
  pageName: string;
  pages: readonly string[];
  locales: readonly string[];
  headline: string;
  copy: string;
  primaryComposition: string;
  secondaryCompositions: readonly string[];
  trustRequirement: string;
  informationDensity: string;
  motionIntensity: string;
  interactionDensity: string;
  scrollBehavior: string;
  showcaseBehavior: string;
  motionAccessibility: string;
  hasNewsletter: boolean;
};

const labels: Record<string, Record<string, string>> = {
  en: { home: "Home", expertise: "Expertise", about: "About", contact: "Contact", capabilities: "Capabilities", trust: "Trust", menu: "Menu", story: "Story", work: "Work", studio: "Studio", collection: "Collection", craft: "Craft", product: "Product", developers: "Developers", security: "Security", services: "Services", approach: "Approach", care: "Care", solutions: "Solutions", pricing: "Pricing" },
  tr: { home: "Ana sayfa", expertise: "Uzmanlık", about: "Hakkımızda", contact: "İletişim", capabilities: "Yetenekler", trust: "Güven", menu: "Menü", story: "Hikâye", work: "Projeler", studio: "Stüdyo", collection: "Koleksiyon", craft: "Zanaat", product: "Ürün", developers: "Geliştiriciler", security: "Güvenlik", services: "Hizmetler", approach: "Yaklaşım", care: "Bakım", solutions: "Çözümler", pricing: "Fiyatlandırma" },
};

const focusByCategory: Record<string, readonly string[]> = {
  "law firm": ["Judgment", "Evidence", "Continuity"],
  security: ["Threat model", "Controls", "Verification"],
  restaurant: ["Menu", "Place", "Experience"],
  "architecture studio": ["Context", "Material", "Craft"],
  furniture: ["Material", "Proportion", "Longevity"],
  "developer platform": ["Workflow", "Reliability", "Integration"],
  "financial services": ["Risk", "Clarity", "Stewardship"],
  healthcare: ["Care", "Access", "Trust"],
  saas: ["Outcome", "Workflow", "Proof"],
  "professional services": ["Expertise", "Approach", "Trust"],
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

function ContextSections(props: Props) {
  const focus = focusByCategory[props.businessCategory] ?? focusByCategory["professional services"];
  return (
    <section className="context-grid" aria-label={props.locale === "tr" ? "Yaklaşım" : "Approach"}>
      {focus.map((item, index) => (
        <article className="context-block" key={item} data-motion="reveal" data-motion-index={index}>
          <span className="context-index">0{index + 1}</span>
          <h2>{item}</h2>
          <p>{props.locale === "tr" ? `${props.businessName}, ${item.toLocaleLowerCase("tr-TR")} odağını ${props.audience} için net bir kullanıcı yoluna dönüştürür.` : `${props.businessName} turns ${item.toLowerCase()} into a clear user path for ${props.audience}.`}</p>
        </article>
      ))}
    </section>
  );
}

export function PageShell(props: Props) {
  const t = labels[props.locale] ?? labels.en;
  const compositionClass = `composition-${props.primaryComposition}`;
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
            <a className="language-link" key={locale} href={`/${locale}`} hrefLang={locale}>{locale.toUpperCase()}</a>
          ))}
        </div>
      </header>
      <main id="main" className={compositionClass} data-composition={props.primaryComposition} data-density={props.informationDensity} data-trust={props.trustRequirement} data-motion-intensity={props.motionIntensity} data-interaction-density={props.interactionDensity} data-scroll-behavior={props.scrollBehavior} data-showcase-behavior={props.showcaseBehavior} data-motion-accessibility={props.motionAccessibility}>
        <section className={props.pageName === "home" ? "hero" : "content-block"}>
          <div className="hero-copy" data-motion="reveal">
            <p className="eyebrow">{props.businessCategory}</p>
            <h1>{props.headline}</h1>
            <p className="lede">{props.copy}</p>
            {props.pageName === "home" && <a className="primary-action" href={href(props.locale, "contact")}>{props.locale === "tr" ? "Görüşme başlat" : "Start a conversation"}</a>}
          </div>
          {props.pageName === "home" && (
            <aside className="composition-note" data-interactive="tilt" aria-label={props.locale === "tr" ? "Tasarım yaklaşımı" : "Design approach"}>
              <strong>{props.primaryComposition.replaceAll("-", " ")}</strong>
              <span>{props.secondaryCompositions.join(" · ")}</span>
            </aside>
          )}
          {props.pageName === "contact" && <ContactForm locale={props.locale} />}
          {props.pageName !== "home" && props.pageName !== "contact" && <div className="evidence-line"><strong>{props.locale === "tr" ? "Odak" : "Built around"}</strong><span>{props.audience}</span></div>}
        </section>
        {props.pageName === "home" && <ContextSections {...props} />}
      </main>
      <MotionRuntime />
      <footer>
        {props.hasNewsletter && props.pageName === "home" && <NewsletterForm locale={props.locale} />}
        <p>{props.locale === "tr" ? "Netlik, güven ve ölçülebilir aksiyon için tasarlandı." : "Built for clarity, trust, and measurable action."}</p>
      </footer>
    </>
  );
}
'''



def _motion_runtime_source() -> str:
    return r'''"use client";

import { useEffect } from "react";

export function MotionRuntime() {
  useEffect(() => {
    const root = document.documentElement;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarsePointer = window.matchMedia("(pointer: coarse)");
    const observed = Array.from(document.querySelectorAll<HTMLElement>("[data-motion='reveal']"));
    const interactive = Array.from(document.querySelectorAll<HTMLElement>("[data-interactive='tilt']"));
    let frame = 0;

    const applyMotionPreference = () => {
      root.dataset.reducedMotion = reduceMotion.matches ? "true" : "false";
      if (reduceMotion.matches) observed.forEach((node) => node.classList.add("is-visible"));
    };

    const updateScroll = () => {
      frame = 0;
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      root.style.setProperty("--ilaios-scroll-progress", String(Math.min(1, Math.max(0, window.scrollY / max))));
    };

    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(updateScroll);
    };

    const observer = !reduceMotion.matches && "IntersectionObserver" in window
      ? new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              (entry.target as HTMLElement).classList.add("is-visible");
              observer?.unobserve(entry.target);
            }
          });
        }, { threshold: 0.16, rootMargin: "0px 0px -8% 0px" })
      : null;

    observed.forEach((node) => observer?.observe(node));
    if (!observer) observed.forEach((node) => node.classList.add("is-visible"));

    const cleanups = interactive.map((node) => {
      const onPointerMove = (event: PointerEvent) => {
        if (reduceMotion.matches || coarsePointer.matches) return;
        const rect = node.getBoundingClientRect();
        const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / Math.max(1, rect.width)));
        const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / Math.max(1, rect.height)));
        node.style.setProperty("--pointer-x", String(x));
        node.style.setProperty("--pointer-y", String(y));
      };
      const reset = () => {
        node.style.removeProperty("--pointer-x");
        node.style.removeProperty("--pointer-y");
      };
      node.addEventListener("pointermove", onPointerMove, { passive: true });
      node.addEventListener("pointerleave", reset);
      return () => {
        node.removeEventListener("pointermove", onPointerMove);
        node.removeEventListener("pointerleave", reset);
      };
    });

    applyMotionPreference();
    updateScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    reduceMotion.addEventListener("change", applyMotionPreference);

    return () => {
      observer?.disconnect();
      cleanups.forEach((cleanup) => cleanup());
      window.removeEventListener("scroll", onScroll);
      reduceMotion.removeEventListener("change", applyMotionPreference);
      if (frame) window.cancelAnimationFrame(frame);
      root.style.removeProperty("--ilaios-scroll-progress");
      delete root.dataset.reducedMotion;
    };
  }, []);

  return null;
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
:root{--ink:#101828;--muted:#475467;--line:#d0d5dd;--accent:#0b5fff;--surface:#f8fafc;--max:1180px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:#fff;line-height:1.55}a{color:inherit}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.skip-link{position:absolute;left:-999px;top:0}.skip-link:focus{left:1rem;top:1rem;background:#fff;padding:.75rem;z-index:10}.site-header{max-width:var(--max);margin:auto;padding:1.2rem 1.5rem;display:grid;grid-template-columns:auto 1fr auto;gap:clamp(1.25rem,3vw,3rem);align-items:center;border-bottom:1px solid var(--line)}.brand{font-weight:800;text-decoration:none}nav{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap}nav a,.languages a{display:inline-flex;align-items:center;min-height:40px;text-decoration:none}main{max-width:var(--max);margin:auto;padding:clamp(2rem,6vw,6rem) 1.5rem}.hero{min-height:58vh;display:grid;align-content:center;gap:clamp(2rem,5vw,5rem)}.hero-copy{max-width:780px}.hero h1,.content-block h1{font-size:clamp(2.6rem,7vw,6rem);line-height:1;letter-spacing:-.05em;max-width:13ch;margin:.4rem 0 1.4rem}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.78rem;font-weight:700;color:var(--muted)}.lede{font-size:clamp(1.05rem,1.8vw,1.35rem);max-width:60ch}.primary-action{display:inline-flex;align-items:center;min-height:44px;width:max-content;margin-top:1.5rem;background:var(--ink);color:#fff;padding:.75rem 1rem;text-decoration:none}.composition-note{border-left:1px solid var(--line);padding-left:1rem;display:grid;gap:.35rem;align-content:end;color:var(--muted);text-transform:capitalize}.composition-note strong{color:var(--ink)}.context-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--line);margin-top:clamp(1rem,4vw,4rem);border:1px solid var(--line)}.context-block{background:#fff;padding:clamp(1.25rem,3vw,2.5rem);min-height:220px}.context-index{font-size:.75rem;color:var(--muted)}.context-block h2{font-size:clamp(1.4rem,2.5vw,2.2rem);margin:2rem 0 .75rem}.content-block{max-width:850px}.evidence-line{display:grid;grid-template-columns:140px 1fr;gap:1rem;border-top:1px solid var(--line);padding-top:1rem;margin-top:3rem}.contact-form{display:grid;gap:.65rem;margin-top:2rem;max-width:620px}.contact-form input,.contact-form textarea,.newsletter-form input{font:inherit;padding:.8rem;border:1px solid var(--line)}.contact-form textarea{min-height:150px}.contact-form button,.newsletter-form button{font:inherit;min-height:44px;padding:.75rem 1rem;border:0;background:var(--ink);color:#fff;width:max-content}.newsletter-form{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.5rem 1rem;align-items:end;max-width:620px;margin-bottom:1.5rem}.newsletter-form label{grid-column:1/-1;color:var(--ink)}footer{max-width:var(--max);margin:3rem auto 0;padding:2rem 1.5rem;border-top:1px solid var(--line);color:var(--muted)}
.composition-minimal-institutional .hero{grid-template-columns:minmax(0,1.5fr) minmax(220px,.5fr);align-items:end}.composition-minimal-institutional .context-grid{grid-template-columns:1.4fr 1fr 1fr}.composition-technical-flow .hero,.composition-layered-architecture .hero{grid-template-columns:minmax(0,1.15fr) minmax(260px,.85fr);background:linear-gradient(90deg,#fff 0 68%,var(--surface) 68%);padding-left:clamp(1rem,3vw,3rem);padding-right:clamp(1rem,3vw,3rem)}.composition-technical-flow .context-grid,.composition-layered-architecture .context-grid{grid-template-columns:repeat(3,minmax(0,1fr));counter-reset:step}.composition-product-showcase .hero{grid-template-columns:minmax(0,1fr) minmax(280px,.8fr)}.composition-product-showcase .composition-note{background:var(--surface);padding:2rem;border-left:0}.composition-visual-portfolio .hero,.composition-media-led .hero{min-height:70vh;grid-template-columns:minmax(0,.8fr) minmax(300px,1.2fr);align-items:end}.composition-visual-portfolio .context-grid,.composition-media-led .context-grid{grid-template-columns:1.6fr .7fr .7fr}.composition-editorial-split .hero,.composition-narrative-scroll .hero{grid-template-columns:minmax(0,1fr) minmax(240px,.6fr)}.composition-evidence-trust .context-grid{grid-template-columns:1fr 1fr 1fr}.composition-documentation-led .hero{min-height:46vh}.composition-documentation-led .context-grid{grid-template-columns:1fr}.composition-structured-comparison .context-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
[data-density="high"] .context-block{min-height:180px;padding:1.5rem}[data-trust="high"] .context-grid{border-top:3px solid var(--ink)}
[data-motion="reveal"]{opacity:0;transform:translate3d(0,24px,0);transition:opacity .55s ease,transform .7s cubic-bezier(.2,.7,.2,1);transition-delay:calc(var(--motion-delay,0)*70ms);will-change:opacity,transform}[data-motion="reveal"].is-visible{opacity:1;transform:translate3d(0,0,0)}[data-motion-index="1"]{--motion-delay:1}[data-motion-index="2"]{--motion-delay:2}[data-interactive="tilt"]{--pointer-x:.5;--pointer-y:.5;transform:perspective(900px) rotateX(calc((.5 - var(--pointer-y))*4deg)) rotateY(calc((var(--pointer-x) - .5)*6deg));transition:transform .22s ease;transform-origin:center}[data-scroll-behavior="section-linked"] .hero::after,[data-scroll-behavior="narrative-linked"] .hero::after{content:"";display:block;grid-column:1/-1;height:2px;transform:scaleX(var(--ilaios-scroll-progress,0));transform-origin:left;background:var(--accent);opacity:.65}[data-motion-intensity="low"] [data-motion="reveal"]{transform:none;transition-duration:.25s}[data-interaction-density="low"] [data-interactive="tilt"]{transform:none!important}
@media(max-width:768px){.site-header{grid-template-columns:1fr;align-items:start}nav{justify-content:flex-start}.evidence-line{grid-template-columns:1fr}.hero h1,.content-block h1{font-size:clamp(2.5rem,11vw,4.7rem)}.hero,.composition-minimal-institutional .hero,.composition-technical-flow .hero,.composition-layered-architecture .hero,.composition-product-showcase .hero,.composition-visual-portfolio .hero,.composition-media-led .hero,.composition-editorial-split .hero,.composition-narrative-scroll .hero{grid-template-columns:1fr;background:#fff;min-height:auto}.context-grid,.composition-minimal-institutional .context-grid,.composition-visual-portfolio .context-grid,.composition-media-led .context-grid{grid-template-columns:1fr 1fr}.composition-note{border-left:0;border-top:1px solid var(--line);padding:1rem 0 0}.context-block{min-height:auto}}@media(max-width:430px){main{padding-top:2.25rem}.site-header{padding:1rem}nav{display:grid;grid-template-columns:1fr 1fr;gap:.4rem}.context-grid,.composition-minimal-institutional .context-grid,.composition-visual-portfolio .context-grid,.composition-media-led .context-grid{grid-template-columns:1fr}.contact-form button,.newsletter-form button{width:100%}.newsletter-form{grid-template-columns:1fr}}@media(max-width:360px){nav{grid-template-columns:1fr}}@media(max-width:320px){body{font-size:15px}main{padding-left:1rem;padding-right:1rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}[data-motion="reveal"]{opacity:1!important;transform:none!important}[data-interactive="tilt"]{transform:none!important}}
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
