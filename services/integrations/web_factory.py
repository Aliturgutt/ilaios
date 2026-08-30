"""Governed deterministic Web Factory with context-derived native design."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import cast

from services.design_quality import (
    DesignAssessment,
    DesignContext,
    DesignStrategy,
    NativeDesignStrategyEngine,
)
from services.runtime import ExecutionGrant, GrantPolicy
from services.web_3d_integration import (
    Web3DIntegratedBundle,
    integrate_web_3d_into_generated_content,
)
from services.web_3d_runtime import Web3DRuntimePlan, compile_web_3d_runtime_plan

_REQUIRED_VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)
_WEB3D_FEATURES = frozenset(
    {
        "3d-hero",
        "scroll-camera",
        "product-rotation",
        "parallax",
        "particles",
        "webgl-background",
        "3d-typography",
        "pointer-interaction",
    }
)
_WEB3D_EXPLICIT_TERMS = (
    "3d",
    "webgl",
    "webgpu",
    "three-dimensional",
    "three dimensional",
    "üç boyutlu",
    "uc boyutlu",
)


@dataclass(frozen=True, slots=True)
class WebsiteFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class WebsiteSpec:
    """Structured, inspectable requirements derived from one user objective."""

    site_id: str
    business_name: str
    business_category: str
    audience: str
    primary_goal: str
    conversion_objective: str
    locales: tuple[str, ...]
    pages: tuple[str, ...]
    features: tuple[str, ...]
    brand_personality: tuple[str, ...]
    trust_requirement: str
    visual_asset_availability: str
    information_density: str
    device_priority: str = "responsive"

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], asdict(self))

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> WebsiteSpec:
        return cls(
            site_id=_text(value, "site_id"),
            business_name=_text(value, "business_name"),
            business_category=_text(value, "business_category"),
            audience=_text(value, "audience"),
            primary_goal=_text(value, "primary_goal"),
            conversion_objective=_text(value, "conversion_objective"),
            locales=_text_tuple(value, "locales"),
            pages=_text_tuple(value, "pages"),
            features=_text_tuple(value, "features"),
            brand_personality=_text_tuple(value, "brand_personality"),
            trust_requirement=_text(value, "trust_requirement"),
            visual_asset_availability=_text(value, "visual_asset_availability"),
            information_density=_text(value, "information_density"),
            device_priority=_text(value, "device_priority"),
        )


@dataclass(frozen=True, slots=True)
class WebsiteAcceptance:
    manifest_version: str
    site_id: str
    artifact_hash: str
    bundle_id: str
    bundle_path: str
    required_pages: tuple[str, ...]
    official_brand: str
    files: tuple[WebsiteFile, ...]
    accepted: bool
    routes: tuple[str, ...] = ()
    spec_hash: str = ""
    design_strategy: dict[str, object] | None = None
    qa: dict[str, object] | None = None


def derive_website_spec(request_id: str, objective: str) -> WebsiteSpec:
    """Derive a deterministic, bounded WebsiteSpec from a one-prompt objective."""
    if not request_id or not objective or objective != objective.strip():
        raise ValueError("website request and objective must be non-blank and trimmed")
    if len(objective) > 20_000:
        raise ValueError("website objective exceeds one-prompt input limit")
    normalized = " ".join(objective.casefold().split())
    site_id = f"site-{hashlib.sha256(f'{request_id}\0{objective}'.encode()).hexdigest()[:20]}"
    bilingual = any(
        term in normalized
        for term in (
            "bilingual",
            "turkish/english",
            "english/turkish",
            "türkçe/ingilizce",
            "ingilizce/türkçe",
        )
    )
    turkish = any(term in normalized for term in ("türkçe", "turkish", "turkce"))
    english = any(term in normalized for term in ("english", "ingilizce"))
    locales = ("en", "tr") if bilingual or (turkish and english) else (("tr",) if turkish else ("en",))
    category = _category(normalized)
    premium = any(term in normalized for term in ("premium", "luxury", "lüks", "high-end"))
    trust = "high" if category in {"law firm", "security", "financial services", "healthcare"} else "standard"
    visual = "rich" if category in {"restaurant", "architecture studio", "furniture"} else "standard"
    density = "high" if category in {"developer platform", "security", "financial services"} else "medium"
    pages = _pages(category, normalized)
    return WebsiteSpec(
        site_id=site_id,
        business_name=_business_name(objective, category),
        business_category=category,
        audience=_audience(normalized),
        primary_goal="present a credible finished website aligned to the user objective",
        conversion_objective="contact or primary call-to-action conversion",
        locales=locales,
        pages=pages,
        features=_features(normalized, pages),
        brand_personality=("premium", "confident", "clear") if premium else ("clear", "credible", "distinctive"),
        trust_requirement=trust,
        visual_asset_availability=visual,
        information_density=density,
    )


class GovernedWebFactory:
    def __init__(self, grants: GrantPolicy, artifact_root: Path) -> None:
        self._grants = grants
        self._artifact_root = artifact_root
        self._design = NativeDesignStrategyEngine()

    def plan_design(self, context: DesignContext) -> DesignStrategy:
        return self._design.plan(context)

    @staticmethod
    def accept_design_quality(assessment: DesignAssessment) -> None:
        if assessment.evaluator_id != "design.final-polish":
            raise ValueError("unrecognized design quality evaluator")
        if assessment.status != "PASS" or assessment.blocking_findings:
            raise ValueError("website design quality gate failed")

    def build_generated_site(
        self,
        spec: WebsiteSpec,
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> WebsiteAcceptance:
        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="web.build",
            resource=spec.site_id,
            now=now,
        )
        _validate_spec(spec)
        strategy = self.plan_design(
            DesignContext(
                business_category=spec.business_category,
                audience=spec.audience,
                primary_goal=spec.primary_goal,
                conversion_objective=spec.conversion_objective,
                brand_personality=spec.brand_personality,
                content_volume="high" if len(spec.pages) > 5 else "medium",
                product_complexity="high" if len(spec.features) > 4 else "medium",
                trust_requirement=spec.trust_requirement,
                visual_asset_availability=spec.visual_asset_availability,
                information_density=spec.information_density,
                locale=spec.locales[0],
                device_priority=spec.device_priority,
            )
        )
        content = _generated_site_content(spec, strategy)
        web3d_plan: Web3DRuntimePlan | None = None
        web3d_bundle: Web3DIntegratedBundle | None = None
        if _has_web3d_features(spec.features):
            web3d_plan = _compile_web3d_plan(spec.features)
            web3d_bundle = integrate_web_3d_into_generated_content(
                content,
                web3d_plan,
                home_routes=tuple(f"{locale}/index.html" for locale in spec.locales),
            )
            content = web3d_bundle.content
        artifact_hash = _content_hash(content)
        bundle_id = f"ilaios-web-{artifact_hash[:20]}"
        bundle = self._artifact_root / bundle_id
        if bundle.exists():
            _verify_existing(bundle, content)
        else:
            for relative_path, body in content.items():
                path = bundle / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
        files = tuple(
            WebsiteFile(path, hashlib.sha256(body).hexdigest(), len(body))
            for path, body in sorted(content.items())
        )
        routes = _routes(spec)
        qa = _validate_generated_site(bundle, spec, strategy, routes, files)
        if web3d_plan is not None and web3d_bundle is not None:
            qa["web3d"] = {
                "status": "SOURCE_INTEGRATED_NOT_BROWSER_CERTIFIED",
                "runtime_path": web3d_bundle.runtime_path,
                "plan_sha256": web3d_plan.plan_sha256,
                "runtime_source_sha256": web3d_bundle.runtime_source_sha256,
                "bundle_sha256": web3d_bundle.bundle_sha256,
                "features": list(web3d_plan.features),
            }
        spec_hash = hashlib.sha256(
            json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        acceptance = WebsiteAcceptance(
            "2.0",
            spec.site_id,
            artifact_hash,
            bundle_id,
            str(bundle),
            spec.pages,
            spec.business_name,
            files,
            bool(qa["passed"]),
            routes,
            spec_hash,
            _strategy_dict(strategy),
            qa,
        )
        _write_acceptance(bundle, acceptance, spec)
        self._grants.record_side_effect(grant, spec.site_id)
        return acceptance

    def build_official_site(
        self,
        site_id: str,
        pages: tuple[str, ...],
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> WebsiteAcceptance:
        """Preserve the existing deterministic official-site golden workflow."""
        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="web.build",
            resource=site_id,
            now=now,
        )
        if site_id != "ilaios-official":
            raise ValueError("official website requires the canonical site identity")
        required = ("home", "product", "security", "contact")
        if tuple(sorted(set(pages))) != tuple(sorted(required)):
            raise ValueError("official website requires the canonical page set")
        content = _site_content(required)
        artifact_hash = _content_hash(content)
        bundle_id = f"ilaios-site-{artifact_hash[:20]}"
        bundle = self._artifact_root / bundle_id
        if bundle.exists():
            _verify_existing(bundle, content)
        else:
            bundle.mkdir(parents=True)
            for relative_path, body in content.items():
                path = bundle / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
        files = tuple(
            WebsiteFile(path, hashlib.sha256(body).hexdigest(), len(body))
            for path, body in sorted(content.items())
        )
        _validate_site(bundle, required, files)
        acceptance = WebsiteAcceptance(
            "1.0", site_id, artifact_hash, bundle_id, str(bundle), required, "ILAIOS", files, True
        )
        manifest_path = bundle / "acceptance.json"
        manifest_bytes = json.dumps(
            {
                "accepted": True,
                "artifact_hash": artifact_hash,
                "brand": "ILAIOS",
                "bundle_id": bundle_id,
                "files": [
                    {"path": item.relative_path, "sha256": item.sha256, "size": item.size}
                    for item in files
                ],
                "manifest_version": "1.0",
                "required_pages": required,
                "site_id": site_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
            raise ValueError("website acceptance manifest was tampered")
        manifest_path.write_bytes(manifest_bytes)
        self._grants.record_side_effect(grant, site_id)
        return acceptance


def _category(normalized: str) -> str:
    rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("law firm", ("law firm", "lawyer", "legal", "hukuk", "avukat")),
        ("security", ("cybersecurity", "security company", "siber güvenlik")),
        ("restaurant", ("restaurant", "restoran", "cafe", "café")),
        ("architecture studio", ("architecture studio", "architect", "mimarlık")),
        ("furniture", ("furniture", "mobilya")),
        ("developer platform", ("developer platform", "api platform", "developer tool")),
        ("financial services", ("financial", "finance", "finans")),
        ("healthcare", ("healthcare", "clinic", "medical", "sağlık", "klinik")),
        ("saas", ("saas", "software company", "yazılım şirket")),
    )
    for category, terms in rules:
        if any(term in normalized for term in terms):
            return category
    return "professional services"


def _business_name(objective: str, category: str) -> str:
    match = re.search(r"\bfor\s+([A-Z][A-Za-z0-9&' -]{1,48})", objective)
    if match:
        candidate = match.group(1).strip(" .,-")
        candidate = re.split(r"\b(?:focused|with|that|to|for)\b", candidate, maxsplit=1)[0].strip()
        if candidate:
            return candidate
    names = {
        "law firm": "Northstar Legal",
        "security": "Sentinel Security",
        "restaurant": "Atelier Table",
        "architecture studio": "Form & Field",
        "furniture": "Arc Furniture",
        "developer platform": "Vector Platform",
        "financial services": "Meridian Capital",
        "healthcare": "Northwell Clinic",
        "saas": "Signal Software",
        "professional services": "Independent Studio",
    }
    return names[category]


def _audience(normalized: str) -> str:
    if any(term in normalized for term in ("corporate", "enterprise", "kurumsal")):
        return "corporate and enterprise decision makers"
    if any(term in normalized for term in ("consumer", "b2c")):
        return "consumer customers"
    if "developer" in normalized:
        return "developers and technical teams"
    return "prospective customers and decision makers"


def _pages(category: str, normalized: str) -> tuple[str, ...]:
    category_pages = {
        "law firm": ("home", "expertise", "about", "contact"),
        "security": ("home", "capabilities", "trust", "contact"),
        "restaurant": ("home", "menu", "story", "contact"),
        "architecture studio": ("home", "work", "studio", "contact"),
        "furniture": ("home", "collection", "craft", "contact"),
        "developer platform": ("home", "product", "developers", "security", "contact"),
        "financial services": ("home", "services", "approach", "trust", "contact"),
        "healthcare": ("home", "services", "care", "contact"),
        "saas": ("home", "product", "solutions", "security", "contact"),
        "professional services": ("home", "services", "about", "contact"),
    }
    pages = category_pages[category]
    if "pricing" in normalized and "pricing" not in pages:
        return (*pages[:-1], "pricing", "contact")
    return pages


def _features(normalized: str, pages: tuple[str, ...]) -> tuple[str, ...]:
    features: list[str] = []
    if "contact" in pages:
        features.append("contact-form")
    if any(term in normalized for term in ("blog", "articles", "makale")):
        features.append("content")
    if any(term in normalized for term in ("newsletter", "bülten")):
        features.append("newsletter")
    if any(term in normalized for term in ("search", "arama")):
        features.append("search")
    if any(term in normalized for term in _WEB3D_EXPLICIT_TERMS):
        web3d = compile_web_3d_runtime_plan(f"website {normalized}")
        features.extend(feature for feature in web3d.features if feature not in features)
    return tuple(features)


def _has_web3d_features(features: tuple[str, ...]) -> bool:
    return bool(set(features).intersection(_WEB3D_FEATURES))


def _compile_web3d_plan(features: tuple[str, ...]) -> Web3DRuntimePlan:
    selected = [feature for feature in features if feature in _WEB3D_FEATURES]
    if not selected:
        raise ValueError("3D runtime plan requires explicit 3D features")
    phrases = {
        "3d-hero": "3D hero",
        "scroll-camera": "scroll camera",
        "product-rotation": "product model rotation",
        "parallax": "parallax",
        "particles": "particles",
        "webgl-background": "WebGL background",
        "3d-typography": "3D typography",
        "pointer-interaction": "pointer touch interaction",
    }
    objective = "Build a website with explicit 3D capability: " + ", ".join(
        phrases[feature] for feature in selected
    ) + "."
    plan = compile_web_3d_runtime_plan(objective)
    if set(plan.features) != set(selected):
        raise ValueError("3D runtime plan did not preserve the requested feature set")
    return plan


def _validate_spec(spec: WebsiteSpec) -> None:
    if not spec.site_id.startswith("site-"):
        raise ValueError("generated website requires canonical generated site identity")
    if not spec.pages or len(set(spec.pages)) != len(spec.pages):
        raise ValueError("generated website pages must be non-empty and unique")
    if "home" not in spec.pages or "contact" not in spec.pages:
        raise ValueError("generated website requires home and contact routes")
    if not spec.locales or not set(spec.locales) <= {"en", "tr"}:
        raise ValueError("generated website locales must be en/tr")
    for value in (
        spec.business_name,
        spec.business_category,
        spec.audience,
        spec.primary_goal,
        spec.conversion_objective,
    ):
        if not value.strip():
            raise ValueError("generated website spec fields must be non-empty")


def _routes(spec: WebsiteSpec) -> tuple[str, ...]:
    return tuple(
        f"{locale}/{'index.html' if page == 'home' else f'{page}.html'}"
        for locale in spec.locales
        for page in spec.pages
    )


def _generated_site_content(spec: WebsiteSpec, strategy: DesignStrategy) -> dict[str, bytes]:
    content: dict[str, bytes] = {}
    origin = f"https://{spec.site_id}.local"
    for locale in spec.locales:
        navigation = " ".join(
            f'<a href="{escape("index.html" if page == "home" else f"{page}.html")}">{escape(_label(page, locale))}</a>'
            for page in spec.pages
        )
        languages = " ".join(
            f'<a class="language-link" href="../{other}/index.html" hreflang="{other}">{other.upper()}</a>'
            for other in spec.locales
            if other != locale
        )
        for page in spec.pages:
            filename = "index.html" if page == "home" else f"{page}.html"
            route = f"{locale}/{filename}"
            title = _label(page, locale)
            description = _description(spec, page, locale)
            canonical = f"{origin}/{route}"
            body = _page_body(spec, page, locale, strategy)
            html = f'''<!doctype html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{escape(description)}">
<meta name="robots" content="index,follow">
<meta property="og:title" content="{escape(spec.business_name)} — {escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:type" content="website">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'self'">
<link rel="canonical" href="{escape(canonical)}">
<title>{escape(spec.business_name)} — {escape(title)}</title>
<link rel="stylesheet" href="../assets/site.css">
</head>
<body class="composition-{escape(strategy.primary_composition)}">
<a class="skip-link" href="#main">{escape(_t(locale, "Skip to content", "İçeriğe geç"))}</a>
<header class="site-header">
<a class="brand" href="index.html">{escape(spec.business_name)}</a>
<nav aria-label="{escape(_t(locale, "Primary navigation", "Ana navigasyon"))}">{navigation}</nav>
<div class="languages">{languages}</div>
</header>
<main id="main">{body}</main>
<footer><p>{escape(_t(locale, "Built for clarity, trust, and measurable action.", "Netlik, güven ve ölçülebilir aksiyon için tasarlandı."))}</p></footer>
</body>
</html>
'''
            content[route] = html.encode()
    content["assets/site.css"] = _css(strategy).encode()
    content["robots.txt"] = b"User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    urls = "".join(f"<url><loc>{origin}/{escape(route)}</loc></url>" for route in _routes(spec))
    content["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    ).encode()
    return content


def _page_body(spec: WebsiteSpec, page: str, locale: str, strategy: DesignStrategy) -> str:
    if page == "home":
        return (
            f'<section class="hero"><p class="eyebrow">{escape(spec.business_category.title())}</p>'
            f'<h1>{escape(_home_headline(spec, locale))}</h1>'
            f'<p class="lede">{escape(_home_copy(spec, locale))}</p>'
            f'<a class="primary-action" href="contact.html">{escape(_t(locale, "Start a conversation", "Görüşme başlat"))}</a></section>'
            f"{_proof_section(spec, locale, strategy)}"
        )
    if page == "contact":
        return (
            f'<section class="content-block"><h1>{escape(_label(page, locale))}</h1>'
            f'<p>{escape(_t(locale, "Tell us what outcome you need. We will respond with a clear next step.", "İhtiyacınız olan sonucu anlatın. Net bir sonraki adımla dönüş yapalım."))}</p>'
            '<form method="post" action="#">'
            f'<label for="name">{escape(_t(locale, "Name", "Ad"))}</label><input id="name" name="name" autocomplete="name" required>'
            f'<label for="email">{escape(_t(locale, "Email", "E-posta"))}</label><input id="email" name="email" type="email" autocomplete="email" required>'
            f'<label for="message">{escape(_t(locale, "Message", "Mesaj"))}</label><textarea id="message" name="message" required></textarea>'
            f'<button type="submit">{escape(_t(locale, "Send request", "Talebi gönder"))}</button></form></section>'
        )
    return (
        f'<section class="content-block"><p class="eyebrow">{escape(spec.business_category.title())}</p>'
        f'<h1>{escape(_label(page, locale))}</h1><p class="lede">{escape(_description(spec, page, locale))}</p>'
        f'<div class="evidence-line"><strong>{escape(_t(locale, "Built around", "Odak"))}</strong>'
        f"<span>{escape(spec.audience)}</span></div></section>"
    )


def _proof_section(spec: WebsiteSpec, locale: str, strategy: DesignStrategy) -> str:
    return (
        '<section class="proof-band" aria-label="Evidence">'
        f"<h2>{escape(_t(locale, 'Why this structure works', 'Bu yapı neden çalışır'))}</h2>"
        f"<p>{escape(_t(locale, 'The information architecture, hierarchy, and interaction model are derived from the business context rather than a fixed template.', 'Bilgi mimarisi, hiyerarşi ve etkileşim modeli sabit bir şablondan değil iş bağlamından türetilir.'))}</p>"
        f'<dl><div><dt>{escape(_t(locale, "Audience", "Hedef kitle"))}</dt><dd>{escape(spec.audience)}</dd></div>'
        f'<div><dt>{escape(_t(locale, "Composition", "Kompozisyon"))}</dt><dd>{escape(strategy.primary_composition)}</dd></div>'
        f'<div><dt>{escape(_t(locale, "Trust posture", "Güven seviyesi"))}</dt><dd>{escape(spec.trust_requirement)}</dd></div></dl></section>'
    )


def _home_headline(spec: WebsiteSpec, locale: str) -> str:
    en = {
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
    tr = {
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
    return tr if locale == "tr" else en


def _home_copy(spec: WebsiteSpec, locale: str) -> str:
    if locale == "tr":
        return f"{spec.business_name}, {spec.audience} için güvenilir, erişilebilir ve amaca dönük bir dijital deneyim sunar."
    return f"{spec.business_name} presents a credible, accessible, outcome-oriented experience for {spec.audience}."


def _description(spec: WebsiteSpec, page: str, locale: str) -> str:
    if locale == "tr":
        return f"{spec.business_name} için {_label(page, locale).lower()} sayfası; güven, netlik ve kullanıcı aksiyonu için yapılandırılmıştır."
    return f"{_label(page, locale)} for {spec.business_name}, structured for trust, clarity, and user action."


def _label(page: str, locale: str) -> str:
    tr = {
        "home": "Ana sayfa", "expertise": "Uzmanlık", "about": "Hakkımızda", "contact": "İletişim",
        "capabilities": "Yetenekler", "trust": "Güven", "menu": "Menü", "story": "Hikâye",
        "work": "Projeler", "studio": "Stüdyo", "collection": "Koleksiyon", "craft": "Zanaat",
        "product": "Ürün", "developers": "Geliştiriciler", "security": "Güvenlik", "services": "Hizmetler",
        "approach": "Yaklaşım", "care": "Bakım", "solutions": "Çözümler", "pricing": "Fiyatlandırma",
    }
    return tr.get(page, page.replace("-", " ").title()) if locale == "tr" else page.replace("-", " ").title()


def _t(locale: str, en: str, tr: str) -> str:
    return tr if locale == "tr" else en


def _css(strategy: DesignStrategy) -> str:
    gap = "clamp(1rem,2vw,1.8rem)" if strategy.type_behavior == "dense-technical" else "clamp(1.25rem,3vw,3rem)"
    template = """
:root{--ink:#101828;--muted:#475467;--line:#d0d5dd;--paper:#f8fafc;--accent:#0b5fff;--max:1180px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:white;line-height:1.55}a{color:inherit}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.skip-link{position:absolute;left:-999px;top:0}.skip-link:focus{left:1rem;top:1rem;background:white;padding:.75rem;z-index:10}.site-header{max-width:var(--max);margin:auto;padding:1.2rem 1.5rem;display:grid;grid-template-columns:auto 1fr auto;gap:__GAP__;align-items:center;border-bottom:1px solid var(--line)}.brand{font-weight:800;text-decoration:none;letter-spacing:-.02em}nav{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap}nav a,.language-link{text-decoration:none}nav a:hover{text-decoration:underline}
main{max-width:var(--max);margin:auto;padding:clamp(2rem,6vw,6rem) 1.5rem}.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.55fr);column-gap:clamp(2rem,6vw,7rem);align-items:end;min-height:58vh}.hero .eyebrow,.hero h1,.hero .lede,.hero .primary-action{grid-column:1}.hero h1{font-size:clamp(2.6rem,7vw,6.6rem);line-height:.98;letter-spacing:-.055em;margin:.4rem 0 1.4rem;max-width:12ch}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.78rem;font-weight:700;color:var(--muted)}.lede{font-size:clamp(1.05rem,1.8vw,1.35rem);max-width:60ch}.primary-action{display:inline-block;width:max-content;margin-top:1.5rem;background:var(--ink);color:white;padding:.9rem 1.1rem;text-decoration:none}
.proof-band{margin-top:clamp(3rem,8vw,8rem);border-top:1px solid var(--line);padding-top:2rem;display:grid;grid-template-columns:.7fr 1fr;gap:__GAP__}.proof-band dl{grid-column:2;display:grid;gap:.8rem}.proof-band dl div{display:grid;grid-template-columns:150px 1fr;border-top:1px solid var(--line);padding-top:.75rem}dt{font-weight:700}dd{margin:0;color:var(--muted)}.content-block{max-width:850px}.content-block h1{font-size:clamp(2.4rem,6vw,5.3rem);line-height:1;letter-spacing:-.045em}.evidence-line{display:grid;grid-template-columns:140px 1fr;gap:1rem;border-top:1px solid var(--line);padding-top:1rem;margin-top:3rem}form{display:grid;gap:.65rem;margin-top:2rem;max-width:620px}input,textarea{font:inherit;padding:.8rem;border:1px solid var(--line);border-radius:0}textarea{min-height:150px}button{font:inherit;padding:.9rem 1rem;border:0;background:var(--ink);color:white;width:max-content}footer{max-width:var(--max);margin:3rem auto 0;padding:2rem 1.5rem;border-top:1px solid var(--line);color:var(--muted)}
.composition-technical-flow .hero,.composition-layered-architecture .hero{grid-template-columns:minmax(0,1.15fr) minmax(260px,.45fr)}.composition-minimal-institutional main{max-width:1050px}.composition-visual-portfolio .hero,.composition-media-led .hero{min-height:68vh}.composition-product-showcase .hero{grid-template-columns:minmax(0,1.1fr) minmax(240px,.5fr)}
@media (max-width:1024px){.hero{grid-template-columns:1fr;min-height:auto}.proof-band{grid-template-columns:1fr}.proof-band dl{grid-column:1}}@media (max-width:768px){.site-header{grid-template-columns:1fr;align-items:start}nav{justify-content:flex-start}.hero h1{font-size:clamp(2.5rem,11vw,4.7rem)}.proof-band dl div,.evidence-line{grid-template-columns:1fr}}@media (max-width:430px){main{padding-top:2.25rem}.site-header{padding:1rem}nav{display:grid;grid-template-columns:1fr 1fr;gap:.65rem}.primary-action,button{width:100%;text-align:center}}@media (max-width:412px){.site-header{gap:.8rem}}@media (max-width:390px){.hero h1{font-size:2.7rem}}@media (max-width:360px){nav{grid-template-columns:1fr}}@media (max-width:320px){body{font-size:15px}main{padding-left:1rem;padding-right:1rem}}@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
""".strip()
    return template.replace("__GAP__", gap)


def _validate_generated_site(
    bundle: Path,
    spec: WebsiteSpec,
    strategy: DesignStrategy,
    routes: tuple[str, ...],
    files: tuple[WebsiteFile, ...],
) -> dict[str, object]:
    expected = {*routes, "assets/site.css", "robots.txt", "sitemap.xml"}
    if any(item.relative_path == "assets/3d/index.html" for item in files):
        expected.add("assets/3d/index.html")
    actual = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "acceptance.json"
    }
    if actual != expected:
        raise ValueError("generated website artifact file set is incomplete")
    file_map = {item.relative_path: item for item in files}
    for route in routes:
        body = (bundle / route).read_text(encoding="utf-8")
        required_fragments = (
            "<!doctype html>", '<meta name="viewport"', "Content-Security-Policy",
            'class="skip-link"', '<main id="main">', "<h1>", "../assets/site.css",
            'rel="canonical"', 'property="og:title"',
        )
        if any(fragment not in body for fragment in required_fragments):
            raise ValueError("generated website semantic/security/SEO validation failed")
        if f'class="composition-{strategy.primary_composition}"' not in body:
            raise ValueError("generated website design strategy was not applied")
        if "lorem ipsum" in body.casefold():
            raise ValueError("generated website contains placeholder copy")
        encoded = body.encode()
        item = file_map[route]
        if hashlib.sha256(encoded).hexdigest() != item.sha256:
            raise ValueError("generated website file hash validation failed")
    css = (bundle / "assets/site.css").read_text(encoding="utf-8")
    for width in _REQUIRED_VIEWPORTS:
        if width < 768 and f"max-width:{width}px" not in css:
            raise ValueError("generated website responsive evidence is incomplete")
    if "@media (prefers-reduced-motion:reduce)" not in css or ":focus-visible" not in css:
        raise ValueError("generated website accessibility behavior is incomplete")
    return {
        "passed": True,
        "build": "PASS",
        "navigation": "PASS",
        "responsive_structural": "PASS",
        "accessibility_structural": "PASS",
        "seo_predeploy": "PASS",
        "security_static": "PASS",
        "design_strategy_applied": "PASS",
        "placeholder_copy": "PASS",
        "covered_viewports": _REQUIRED_VIEWPORTS,
        "covered_locales": spec.locales,
        "browser_runtime_evidence": "REQUIRED_IN_CI_OR_DEPLOYMENT_CERTIFICATION",
        "deployment_state": "NOT_DEPLOYED",
    }


def _write_acceptance(bundle: Path, acceptance: WebsiteAcceptance, spec: WebsiteSpec) -> None:
    manifest_path = bundle / "acceptance.json"
    manifest = {
        "accepted": acceptance.accepted,
        "artifact_hash": acceptance.artifact_hash,
        "brand": acceptance.official_brand,
        "bundle_id": acceptance.bundle_id,
        "design_strategy": acceptance.design_strategy,
        "files": [{"path": item.relative_path, "sha256": item.sha256, "size": item.size} for item in acceptance.files],
        "manifest_version": acceptance.manifest_version,
        "qa": acceptance.qa,
        "required_pages": acceptance.required_pages,
        "routes": acceptance.routes,
        "site_id": acceptance.site_id,
        "spec": spec.to_dict(),
        "spec_hash": acceptance.spec_hash,
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    if manifest_path.exists() and manifest_path.read_bytes() != encoded:
        raise ValueError("website acceptance manifest was tampered")
    manifest_path.write_bytes(encoded)


def _strategy_dict(strategy: DesignStrategy) -> dict[str, object]:
    return {
        "primary_composition": strategy.primary_composition,
        "secondary_compositions": strategy.secondary_compositions,
        "type_behavior": strategy.type_behavior,
        "spacing_behavior": strategy.spacing_behavior,
        "surface_behavior": strategy.surface_behavior,
        "imagery_behavior": strategy.imagery_behavior,
        "cta_hierarchy": strategy.cta_hierarchy,
        "diagram_usage": strategy.diagram_usage,
        "motion_intensity": strategy.motion_intensity,
        "navigation_behavior": strategy.navigation_behavior,
        "mobile_transformation": strategy.mobile_transformation,
    }


def _content_hash(content: dict[str, bytes]) -> str:
    material = b"".join(path.encode() + b"\0" + body + b"\0" for path, body in sorted(content.items()))
    return hashlib.sha256(material).hexdigest()


def _site_content(pages: tuple[str, ...]) -> dict[str, bytes]:
    navigation = "".join(f'<a href="{page}.html">{page.title()}</a>' for page in pages)
    messages = {
        "home": "Governed intelligence for durable outcomes.",
        "product": "ILAIOS coordinates agents, evidence, and delivery.",
        "security": "Fail-closed grants and tamper-evident execution.",
        "contact": "Contact the ILAIOS team through governed channels.",
    }
    files = {
        f"{page}.html": (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<title>ILAIOS | {page.title()}</title>"
            '<link rel="stylesheet" href="assets/site.css"></head><body>'
            f"<header><strong>ILAIOS</strong><nav>{navigation}</nav></header>"
            f"<main><h1>{page.title()}</h1><p>{messages[page]}</p></main></body></html>"
        ).encode()
        for page in pages
    }
    files["assets/site.css"] = b"body{font-family:sans-serif;margin:2rem;color:#17223b}header{display:flex;justify-content:space-between}nav a{margin:.5rem}"
    return files


def _verify_existing(bundle: Path, expected: dict[str, bytes]) -> None:
    actual_paths = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "acceptance.json"
    }
    if actual_paths != set(expected):
        raise ValueError("website artifact bundle file set was tampered")
    for relative_path, body in expected.items():
        if (bundle / relative_path).read_bytes() != body:
            raise ValueError("website artifact bundle content was tampered")


def _validate_site(bundle: Path, required: tuple[str, ...], files: tuple[WebsiteFile, ...]) -> None:
    file_map = {item.relative_path: item for item in files}
    for page in required:
        relative_path = f"{page}.html"
        body = (bundle / relative_path).read_text(encoding="utf-8")
        if "ILAIOS" not in body or f"<h1>{page.title()}</h1>" not in body:
            raise ValueError("website brand or page content validation failed")
        for target in required:
            if f'href="{target}.html"' not in body:
                raise ValueError("website navigation validation failed")
        item = file_map[relative_path]
        encoded = body.encode()
        if hashlib.sha256(encoded).hexdigest() != item.sha256:
            raise ValueError("website file hash validation failed")


def _text(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"website spec {key} is invalid")
    return item


def _text_tuple(value: dict[str, object], key: str) -> tuple[str, ...]:
    item = value.get(key)
    if not isinstance(item, (list, tuple)) or not all(isinstance(row, str) and row for row in item):
        raise ValueError(f"website spec {key} is invalid")
    return tuple(cast(list[str] | tuple[str, ...], item))
