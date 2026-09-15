from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

from services.design_quality import REQUIRED_VIEWPORTS, DesignObservation
from services.integrations.web_factory import GovernedWebFactory, derive_website_spec
from services.integrations.web_project import materialize_next_project
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy
from services.web_screenshot_fidelity import assess_visual_quality


OBJECTIVE = (
    "Build a premium bilingual Turkish/English corporate developer platform website for ILAIOS, "
    "a governed AI operating system that turns authenticated goals into governed, validated "
    "finished-product workflows with evidence. Present finished outcomes including Website, Video, "
    "Software, Application and Research, while emphasizing governance, identity, permissions, "
    "evidence, security and developer trust. Use compact typography and spacing, mobile-first "
    "responsive composition, clear navigation, a contact flow, strong accessibility and SEO, and "
    "professional enterprise visual quality. Treat the current www.ilaios.com only as product-truth "
    "and brand reference; create a fresh visual composition rather than copying its current layout."
)

REFERENCE_SITE = "https://www.ilaios.com"
REFERENCE_ROUTES = ("/", "/platform", "/docs", "/trust")
VIEWPORTS = tuple(
    {"width": width, "height": 900 if width >= 1024 else 844 if width <= 430 else 900}
    for width in REQUIRED_VIEWPORTS
)

_MOBILE_GRID_768_FROM = (
    ".context-grid,.composition-minimal-institutional .context-grid,"
    ".composition-visual-portfolio .context-grid,.composition-media-led .context-grid"
    "{grid-template-columns:1fr 1fr}"
)
_MOBILE_GRID_768_TO = (
    ".context-grid,.composition-minimal-institutional .context-grid,"
    ".composition-technical-flow .context-grid,.composition-layered-architecture .context-grid,"
    ".composition-visual-portfolio .context-grid,.composition-media-led .context-grid,"
    ".composition-evidence-trust .context-grid,.composition-structured-comparison .context-grid"
    "{grid-template-columns:1fr 1fr}"
)
_MOBILE_GRID_430_FROM = (
    ".context-grid,.composition-minimal-institutional .context-grid,"
    ".composition-visual-portfolio .context-grid,.composition-media-led .context-grid"
    "{grid-template-columns:1fr}"
)
_MOBILE_GRID_430_TO = (
    ".context-grid,.composition-minimal-institutional .context-grid,"
    ".composition-technical-flow .context-grid,.composition-layered-architecture .context-grid,"
    ".composition-visual-portfolio .context-grid,.composition-media-led .context-grid,"
    ".composition-evidence-trust .context-grid,.composition-structured-comparison .context-grid"
    "{grid-template-columns:1fr}"
)

_PAGE_ARCHITECTURE = r'''
function PageArchitecture(props: Props) {
  const tr = props.locale === "tr";
  if (props.pageName === "product") {
    return <>
      <section className="page-system page-product" aria-labelledby="product-system-title">
        <p className="section-kicker">{tr ? "Ürün modeli" : "Product model"}</p>
        <h2 id="product-system-title">{tr ? "Amaçtan doğrulanmış çıktıya kontrollü akış" : "A controlled path from objective to verified output"}</h2>
        <div className="process-rail">
          {[tr ? "Amaç" : "Objective", tr ? "Yönetilen iş" : "Governed work", tr ? "Üretim" : "Production", tr ? "Doğrulama" : "Verification"].map((item, index) => <div className="process-step" key={item}><span>0{index + 1}</span><strong>{item}</strong></div>)}
        </div>
      </section>
      <section className="split-proof" aria-label={tr ? "Ürün yaklaşımı" : "Product approach"}>
        <div><p className="section-kicker">{tr ? "Kontrol" : "Control"}</p><h2>{tr ? "Kararlar ve eylemler aynı şey değildir." : "Decisions and actions are not the same thing."}</h2></div>
        <p>{tr ? "Üretim akışı; izin, kanıt ve doğrulama sınırlarını görünür tutacak şekilde sunulur." : "The production path keeps permission, evidence, and validation boundaries visible."}</p>
      </section>
    </>;
  }
  if (props.pageName === "developers") {
    return <>
      <section className="page-system page-developers" aria-labelledby="developer-flow-title">
        <p className="section-kicker">{tr ? "Geliştirici akışı" : "Developer flow"}</p>
        <h2 id="developer-flow-title">{tr ? "Entegrasyon yüzeyi önce sözleşmeyi açıklar." : "The integration surface explains the contract first."}</h2>
        <div className="developer-grid">
          <code>request → policy → execution</code><code>evidence → validation → result</code>
        </div>
      </section>
      <section className="developer-notes" aria-label={tr ? "Geliştirici ilkeleri" : "Developer principles"}>
        <article><span>01</span><h3>{tr ? "Açık sınırlar" : "Explicit boundaries"}</h3><p>{tr ? "Kimlik, yetki ve araç sınırları akıştan ayrılmaz." : "Identity, permission, and tool boundaries remain part of the flow."}</p></article>
        <article><span>02</span><h3>{tr ? "Kanıta bağlı sonuç" : "Evidence-bound result"}</h3><p>{tr ? "Doğrulama olmadan tamamlandı iddiası üretilmez." : "Completion is not represented without validation evidence."}</p></article>
      </section>
    </>;
  }
  if (props.pageName === "security") {
    return <>
      <section className="page-system page-security" aria-labelledby="security-model-title">
        <p className="section-kicker">{tr ? "Güven modeli" : "Trust model"}</p>
        <h2 id="security-model-title">{tr ? "Güvenlik iddiası yerine kontrol zinciri" : "A control chain instead of a security claim"}</h2>
        <dl className="control-ledger">
          <div><dt>{tr ? "Kimlik" : "Identity"}</dt><dd>{tr ? "İstek sahibini ve kapsamı bağlar." : "Binds requester and scope."}</dd></div>
          <div><dt>{tr ? "İzin" : "Permission"}</dt><dd>{tr ? "Eylem sınırını görünür tutar." : "Keeps the action boundary explicit."}</dd></div>
          <div><dt>{tr ? "Kanıt" : "Evidence"}</dt><dd>{tr ? "Doğrulama sonucunu izlenebilir kılar." : "Makes validation outcomes traceable."}</dd></div>
        </dl>
      </section>
      <p className="truth-note">{tr ? "Bu sayfa sertifikasyon veya genel kullanılabilirlik iddiası üretmez; yalnız ürünün kontrol yaklaşımını açıklar." : "This page does not assert certification or general availability; it explains the product control approach only."}</p>
    </>;
  }
  if (props.pageName === "contact") {
    return <section className="contact-expectation" aria-label={tr ? "Sonraki adım" : "What happens next"}>
      <span>01</span><div><h2>{tr ? "Talebinizi ve beklediğiniz sonucu yazın." : "Describe the request and the outcome you need."}</h2><p>{tr ? "Form yalnız iletişim akışını gösterir; gönderim davranışı mevcut doğrulanmış adaptör sınırlarında kalır." : "The form represents the contact flow; submission behavior remains within the currently verified adapter boundary."}</p></div>
    </section>;
  }
  return <ContextSections {...props} />;
}
'''

_PAGE_ARCHITECTURE_CSS = r'''
.page-system,.split-proof,.developer-notes,.contact-expectation{margin-top:clamp(3rem,7vw,6rem);border-top:1px solid var(--line);padding-top:clamp(1.5rem,3vw,2.5rem)}
.section-kicker{font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:700}.page-system>h2,.split-proof h2,.contact-expectation h2{font-size:clamp(1.65rem,3.2vw,3.2rem);line-height:1.08;letter-spacing:-.035em;max-width:18ch;margin:.55rem 0 1.6rem}.process-rail{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.process-step{padding:1.25rem 1rem;display:grid;gap:1.4rem;border-right:1px solid var(--line)}.process-step:last-child{border-right:0}.process-step span,.developer-notes span,.contact-expectation>span{font-size:.72rem;color:var(--muted)}.split-proof{display:grid;grid-template-columns:minmax(0,1fr) minmax(240px,.65fr);gap:clamp(2rem,7vw,7rem);align-items:end}.split-proof>p{max-width:48ch}.developer-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line)}.developer-grid code{background:var(--surface);padding:1.4rem;font-size:clamp(.82rem,1.2vw,1rem);overflow-wrap:anywhere}.developer-notes{display:grid;grid-template-columns:1fr 1fr;gap:clamp(1.5rem,4vw,4rem)}.developer-notes article{display:grid;grid-template-columns:48px 1fr;column-gap:1rem}.developer-notes article p{grid-column:2}.control-ledger{display:grid;margin:0}.control-ledger>div{display:grid;grid-template-columns:minmax(120px,.35fr) 1fr;gap:1rem;padding:1rem 0;border-top:1px solid var(--line)}.control-ledger dt{font-weight:700}.control-ledger dd{margin:0;color:var(--muted)}.truth-note{max-width:70ch;padding:1rem 0;border-bottom:1px solid var(--line);color:var(--muted)}.contact-expectation{display:grid;grid-template-columns:80px 1fr;gap:1rem}.contact-expectation h2{max-width:24ch}.brand-mark{position:relative;display:block;width:min(160px,38vw);height:44px;background-repeat:no-repeat;background-position:left center;background-size:contain}.brand-logo-light{background-image:url('/brand/13-ilaios-primary-horizontal-light.jpg')}.brand-logo-dark{display:none;background-image:url('/brand/02-ilaios-primary-horizontal-dark.jpg')}@media(prefers-color-scheme:dark){.brand-logo-light{display:none}.brand-logo-dark{display:block}}
@media(max-width:768px){.process-rail{grid-template-columns:1fr 1fr}.process-step:nth-child(2){border-right:0}.split-proof,.developer-notes{grid-template-columns:1fr}.developer-grid{grid-template-columns:1fr}.contact-expectation{grid-template-columns:48px 1fr}}
@media(max-width:430px){.process-rail{grid-template-columns:1fr}.process-step{border-right:0;border-bottom:1px solid var(--line)}.process-step:last-child{border-bottom:0}.control-ledger>div{grid-template-columns:1fr}.contact-expectation{grid-template-columns:1fr}}
'''

_REFINEMENT_ONE_CSS = r'''
/* visual-quality-refinement-1: compact type + touch target correction */
.hero h1,.content-block h1{font-size:clamp(2.25rem,5vw,4.4rem);line-height:1.02;max-width:15ch;letter-spacing:-.04em}.site-header nav a,.languages a{min-height:44px;padding:.15rem 0}.lede{font-size:clamp(1rem,1.45vw,1.22rem)}
@media(max-width:768px){.hero h1,.content-block h1{font-size:clamp(2.1rem,8.5vw,3.65rem)}}@media(max-width:430px){.hero h1,.content-block h1{font-size:clamp(2rem,10vw,3rem);line-height:1.05}}
'''

_REFINEMENT_TWO_CSS = r'''
/* visual-quality-refinement-2: enterprise rhythm + monochrome interaction surfaces */
:root{--accent:#101828}main{padding-top:clamp(2rem,4vw,4.5rem);padding-bottom:clamp(2rem,4vw,4.5rem)}.hero{min-height:clamp(380px,52vh,560px)}.context-grid{margin-top:clamp(1.5rem,3vw,3rem)}.primary-action,.contact-form button,.newsletter-form button{border:1px solid var(--ink);background:var(--ink);color:#fff}.composition-note{background:transparent!important}.page-system,.split-proof,.developer-notes,.contact-expectation{margin-top:clamp(2.5rem,5vw,4.5rem)}
@media(prefers-color-scheme:dark){:root{--ink:#f5f5f5;--muted:#b6b6b6;--line:#3a3a3a;--surface:#181818;--accent:#f5f5f5}body,.context-block{background:#101010;color:var(--ink)}.site-header,.skip-link{background:#101010}.composition-technical-flow .hero,.composition-layered-architecture .hero{background:#101010}.primary-action,.contact-form button,.newsletter-form button{background:#f5f5f5;color:#101010;border-color:#f5f5f5}}
'''


def _artifact_root() -> Path:
    value = os.environ.get("ILAIOS_WEB_FACTORY_TRIAL_ARTIFACT_DIR", "artifacts/web-factory-ilaios-trial")
    return Path(value).resolve()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and "node_modules" not in item.parts and ".next" not in item.parts):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _apply_trial_responsive_guard(project_root: Path) -> dict[str, object]:
    css_path = project_root / "app" / "globals.css"
    css = css_path.read_text(encoding="utf-8")
    if _MOBILE_GRID_768_FROM not in css or _MOBILE_GRID_430_FROM not in css:
        raise RuntimeError("generated Web responsive grid contract changed unexpectedly")
    patched = css.replace(_MOBILE_GRID_768_FROM, _MOBILE_GRID_768_TO, 1).replace(_MOBILE_GRID_430_FROM, _MOBILE_GRID_430_TO, 1)
    css_path.write_text(patched, encoding="utf-8")
    return {"applied": True, "scope": "generated-candidate-only", "reason": "composition-specific grids must collapse across canonical mobile widths", "production_mutation": False}


def _bind_canonical_brand(project_root: Path) -> dict[str, object]:
    repo = _repository_root()
    assets = {
        "primary_horizontal_dark": repo / "brand/assets/02-ilaios-primary-horizontal-dark.jpg",
        "primary_horizontal_light": repo / "brand/assets/13-ilaios-primary-horizontal-light.jpg",
    }
    public = project_root / "public" / "brand"
    public.mkdir(parents=True, exist_ok=True)
    plan: dict[str, object] = {"mapping": {}, "recolor": False, "filter": False, "production_mutation": False}
    for role, source in assets.items():
        if not source.is_file():
            raise RuntimeError(f"canonical brand asset missing: {source.relative_to(repo)}")
        destination = public / source.name
        shutil.copyfile(source, destination)
        plan["mapping"][role] = {"source": source.relative_to(repo).as_posix(), "candidate_path": f"public/brand/{source.name}", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    return plan


def _apply_page_architecture(project_root: Path) -> dict[str, object]:
    shell_path = project_root / "components/PageShell.tsx"
    css_path = project_root / "app/globals.css"
    shell = shell_path.read_text(encoding="utf-8")
    marker = "const labels: Record<string, Record<string, string>> = {"
    if marker not in shell or "function PageArchitecture" in shell:
        raise RuntimeError("generated PageShell architecture insertion point changed")
    shell = shell.replace(marker, _PAGE_ARCHITECTURE + "\n" + marker, 1)
    brand = '<a className="brand" href={`/${props.locale}`}>{props.businessName}</a>'
    brand_render = '<a className="brand" href={`/${props.locale}`} aria-label="ILAIOS"><span className="brand-mark brand-logo-light" aria-hidden="true" /><span className="brand-mark brand-logo-dark" aria-hidden="true" /></a>'
    if shell.count(brand) != 1:
        raise RuntimeError("generated PageShell brand insertion point changed")
    shell = shell.replace(brand, brand_render, 1)
    generic = '{props.pageName !== "home" && props.pageName !== "contact" && <div className="evidence-line"><strong>{props.locale === "tr" ? "Odak" : "Built around"}</strong><span>{props.audience}</span></div>}'
    if shell.count(generic) != 1:
        raise RuntimeError("generated PageShell generic inner-page block changed")
    shell = shell.replace(generic, '{props.pageName !== "home" && props.pageName !== "contact" && <div className="page-audience"><strong>{props.locale === "tr" ? "Hedef kitle" : "Audience"}</strong><span>{props.audience}</span></div>}', 1)
    home_context = '{props.pageName === "home" && <ContextSections {...props} />}'
    if shell.count(home_context) != 1:
        raise RuntimeError("generated PageShell context insertion point changed")
    shell = shell.replace(home_context, '{props.pageName === "home" ? <ContextSections {...props} /> : <PageArchitecture {...props} />}', 1)
    shell = shell.replace('data-composition={props.primaryComposition}', 'data-page={props.pageName} data-composition={props.primaryComposition}', 1)
    shell_path.write_text(shell, encoding="utf-8")
    css_path.write_text(css_path.read_text(encoding="utf-8") + "\n" + _PAGE_ARCHITECTURE_CSS, encoding="utf-8")
    return {"home": ["hero", "context-grid"], "product": ["intro", "process-rail", "split-proof"], "developers": ["intro", "developer-flow", "developer-notes"], "security": ["intro", "control-ledger", "truth-note"], "contact": ["intro", "form", "next-step"], "production_mutation": False}


def _apply_refinement(project_root: Path, attempt: int, before: dict[str, object]) -> dict[str, object]:
    css_path = project_root / "app/globals.css"
    addition = _REFINEMENT_ONE_CSS if attempt == 1 else _REFINEMENT_TWO_CSS
    css_path.write_text(css_path.read_text(encoding="utf-8") + "\n" + addition, encoding="utf-8")
    return {
        "after_attempt": attempt,
        "file": "app/globals.css",
        "scope": "generated-candidate-only",
        "reason": "compact typography and touch-target correction" if attempt == 1 else "enterprise rhythm, monochrome interaction surfaces, and dark-surface parity",
        "before_metrics": before,
        "production_mutation": False,
    }


def generate() -> int:
    root = _artifact_root()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    request_id = "ilaios-corporate-web-factory-trial-20260910"
    spec = derive_website_spec(request_id, OBJECTIVE)
    now = datetime.now(timezone.utc)
    grant = ExecutionGrant("ilaios-corporate-web-factory-trial-grant", "web-worker", frozenset({"web.build"}), frozenset({spec.site_id}), now + timedelta(minutes=10), BlastRadiusBudget(max_side_effects=1, max_resources=1))
    factory = GovernedWebFactory(GrantPolicy(), root / "generated-bundles")
    acceptance = factory.build_generated_site(spec, grant=grant, now=now)
    if not acceptance.accepted or acceptance.design_strategy is None or acceptance.qa is None or acceptance.qa.get("passed") is not True:
        raise RuntimeError("Web Factory did not produce structurally accepted source")
    project = materialize_next_project(spec, acceptance.design_strategy, root / "materialized-projects")
    destination = root / "source-project"
    shutil.copytree(Path(project.root_path), destination)
    responsive_guard = _apply_trial_responsive_guard(destination)
    brand_plan = _bind_canonical_brand(destination)
    section_plan = _apply_page_architecture(destination)
    source_sha = os.environ.get("ILAIOS_SOURCE_SHA", os.environ.get("GITHUB_SHA", "UNBOUND"))
    manifest = {
        "schema": "ilaios.web-factory.corporate-trial.v2",
        "source_sha": source_sha,
        "request_id": request_id,
        "reference_site": REFERENCE_SITE,
        "reference_mode": "LIVE_PRODUCT_TRUTH_BRAND_AND_DESIGN_ANALYSIS",
        "objective": OBJECTIVE,
        "spec": spec.to_dict(),
        "design_strategy": acceptance.design_strategy,
        "section_plan": section_plan,
        "brand_plan": brand_plan,
        "factory_accepted": acceptance.accepted,
        "factory_qa": acceptance.qa,
        "routes": list(acceptance.routes),
        "factory_materialization_digest": project.digest,
        "source_project_digest": _tree_digest(destination),
        "source_project_id": project.project_id,
        "source_project_path": "source-project",
        "trial_responsive_guard": responsive_guard,
        "production_mutation": False,
        "production_publish_requested": False,
    }
    _write_json(root / "trial-manifest.json", manifest)
    _write_json(root / "section-plan.json", section_plan)
    _write_json(root / "brand-plan.json", brand_plan)
    print(json.dumps(manifest, sort_keys=True, ensure_ascii=False))
    print("ILAIOS_WEB_FACTORY_CORPORATE_TRIAL_GENERATED=PASS")
    return 0


def _next_route(route: str) -> str:
    normalized = "/" + route.lstrip("/")
    if normalized.endswith("/index.html"):
        return normalized[: -len("index.html")]
    if normalized.endswith(".html"):
        return normalized[:-5]
    return normalized


def _reference_snapshot(page: Page, route: str, viewport: dict[str, int], output: Path) -> dict[str, object]:
    response = page.goto(REFERENCE_SITE + route, wait_until="networkidle", timeout=45_000)
    if response is None or response.status >= 400:
        raise RuntimeError(f"reference site route failed: {route}")
    data = page.evaluate("""() => { const style=(el)=>getComputedStyle(el); const h1=document.querySelector('h1'); const sections=[...document.querySelectorAll('main section')]; return {title:document.title, navigation:[...document.querySelectorAll('header nav a')].map(a=>({text:(a.textContent||'').trim(),href:a.getAttribute('href')})).filter(x=>x.text), headings:[...document.querySelectorAll('h1,h2')].slice(0,16).map(h=>({tag:h.tagName,text:(h.textContent||'').trim(),fontSize:style(h).fontSize})), section_count:sections.length, section_classes:sections.map(s=>s.className||''), ctas:[...document.querySelectorAll('a,button')].filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0}).slice(0,24).map(el=>(el.textContent||'').trim()).filter(Boolean), images:[...document.images].slice(0,12).map(img=>({src:img.getAttribute('src'),alt:img.getAttribute('alt')})), colors:{background:style(document.body).backgroundColor,foreground:style(document.body).color}, h1:{fontSize:h1?style(h1).fontSize:null,lineHeight:h1?style(h1).lineHeight:null}, body_width:document.body.getBoundingClientRect().width}; }""")
    slug = "home" if route == "/" else route.strip("/").replace("/", "-")
    page.screenshot(path=str(output / f"reference-{slug}-{viewport['width']}x{viewport['height']}.png"), full_page=True)
    return {"route": route, "viewport": viewport, **data}


def _ingest_reference(browser: Any, root: Path) -> dict[str, object]:
    output = root / "reference-screenshots"
    output.mkdir(parents=True, exist_ok=True)
    observations: list[dict[str, object]] = []
    for viewport in ({"width": 390, "height": 844}, {"width": 1440, "height": 900}):
        context = browser.new_context(viewport=viewport, color_scheme="light")
        for route in REFERENCE_ROUTES:
            page = context.new_page()
            observations.append(_reference_snapshot(page, route, viewport, output))
            page.close()
        context.close()
    report = {
        "schema": "ilaios.web-reference-analysis.v1",
        "reference_site": REFERENCE_SITE,
        "analysis_scope": ["navigation", "page hierarchy", "section order", "typography", "spacing and geometry", "colors and surfaces", "brand assets", "CTA patterns", "media", "mobile behavior", "repeated patterns"],
        "observations": observations,
        "product_truth_policy": "Reference content is evidence only; generated copy must not promote capability, certification, deployment, or availability beyond what the reference visibly supports.",
        "do_not_copy": ["current page composition", "exact section order", "exact copy", "decorative treatment", "layout defects"],
        "production_mutation": False,
    }
    _write_json(root / "reference-report.json", report)
    return report


_METRICS_JS = r'''() => {
const all=[...document.querySelectorAll('body *')].filter(el=>{const r=el.getBoundingClientRect();const s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'});
const rects=all.map(el=>({el,r:el.getBoundingClientRect()}));
const clipped=rects.filter(x=>x.r.left<-1||x.r.right>innerWidth+1).length;
const structural=[...document.querySelectorAll('main > section')].map(el=>({el,r:el.getBoundingClientRect()}));
let overlaps=0;for(let i=1;i<structural.length;i++){if(structural[i].r.top<structural[i-1].r.bottom-2) overlaps++;}
const h1=document.querySelector('main h1');const hs=h1?getComputedStyle(h1):null;const hr=h1?h1.getBoundingClientRect():null;
const touch=[...document.querySelectorAll('header nav a,.primary-action,button')].filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.height>0&&(r.width<44||r.height<44)}).length;
const focus=document.querySelector('header nav a,.primary-action,button,input');let focusFail=0;if(focus){focus.focus();const fs=getComputedStyle(focus);if((fs.outlineStyle==='none'||parseFloat(fs.outlineWidth||'0')<2)&&fs.boxShadow==='none')focusFail=1;focus.blur();}
const placeholders=[...document.querySelectorAll('.placeholder,.visual-placeholder,[data-placeholder]')].filter(el=>(el.textContent||'').trim().length===0&&!el.querySelector('img,svg,canvas')).length;
const sections=[...document.querySelectorAll('main > section')];let whitespace=0;let maxGap=0;for(let i=0;i<sections.length;i++){const r=sections[i].getBoundingClientRect();const text=(sections[i].textContent||'').trim();if(r.height>innerHeight*1.45&&text.length<180)whitespace++;if(i>0){const prev=sections[i-1].getBoundingClientRect();maxGap=Math.max(maxGap,r.top-prev.bottom);}}
const brand=document.querySelector('.brand-mark');const primary=[...document.querySelectorAll('.primary-action')].filter(el=>el.getBoundingClientRect().width>0).length;
const articles=document.querySelectorAll('main article').length;const text=(document.querySelector('main')?.textContent||'').trim();
const h1Lines=h1&&hs&&hr?Math.max(1,Math.round(hr.height/parseFloat(hs.lineHeight||hs.fontSize))):0;
const giant=h1&&hs&&hr?((innerWidth<=430?parseFloat(hs.fontSize)>52:parseFloat(hs.fontSize)>72)||hr.height>innerHeight*.58?1:0):1;
const mobileHierarchy=innerWidth<=430&&h1Lines>4?1:0;const tr=document.documentElement.lang==='tr';const turkish=tr&&h1&&h1.scrollWidth>h1.clientWidth+1?1:0;
const labels=[...document.querySelectorAll('input:not([type=hidden]),textarea')].filter(el=>!el.labels||el.labels.length===0).length;
const alts=[...document.images].filter(img=>img.alt===null).length;
const ratio=(a,b)=>{const p=x=>{const m=x.match(/\d+(?:\.\d+)?/g);return m?m.slice(0,3).map(Number):[0,0,0]};const l=x=>{const c=p(x).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*c[0]+.7152*c[1]+.0722*c[2]};const l1=l(a),l2=l(b);return(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05)};
let contrast=0;for(const el of [...document.querySelectorAll('p,a,button,h1,h2,h3')].slice(0,80)){const s=getComputedStyle(el);let parent=el;let bg='rgba(0, 0, 0, 0)';while(parent&&bg.includes('rgba')&&bg.endsWith(', 0)')){bg=getComputedStyle(parent).backgroundColor;parent=parent.parentElement;}if(bg.includes('rgba')&&bg.endsWith(', 0)'))bg=getComputedStyle(document.body).backgroundColor;if(ratio(s.color,bg)<(parseFloat(s.fontSize)>=24?3:4.5))contrast++;}
const initialOverflow=document.documentElement.scrollWidth-document.documentElement.clientWidth;const old=document.documentElement.style.fontSize;document.documentElement.style.fontSize='200%';const zoomOverflow=document.documentElement.scrollWidth-document.documentElement.clientWidth;document.documentElement.style.fontSize=old;
return {horizontal_overflow:Math.max(0,Math.ceil(initialOverflow)),clipped_elements:clipped,overlapping_elements:overlaps,missing_focus_indicators:focusFail,undersized_touch_targets:touch,contrast_failures:contrast,missing_alt_text:alts,form_label_failures:labels,text_scaling_failures:zoomOverflow>1?1:0,giant_heading_failures:giant,empty_visual_placeholders:placeholders,excessive_whitespace_regions:whitespace,cta_hierarchy_failures:primary>1?1:0,turkish_layout_failures:turkish,mobile_hierarchy_failures:mobileHierarchy,section_rhythm_failures:maxGap>150?1:0,missing_brand_asset_failures:brand?0:1,text_heavy_without_structure:text.length>650&&sections.length<2&&articles<2?1:0,max_heading_px:h1&&hs?parseFloat(hs.fontSize):0,max_section_gap_px:maxGap,h1_lines:h1Lines,section_fingerprint:sections.map(s=>s.className||s.tagName).join('|'),section_count:sections.length,article_count:articles};
}'''


def _collect_attempt(browser: Any, base_url: str, root: Path, routes: tuple[str, ...], attempt: int) -> tuple[list[DesignObservation], list[dict[str, object]]]:
    screenshots = root / "screenshots" / f"attempt-{attempt}"
    screenshots.mkdir(parents=True, exist_ok=True)
    rows: list[DesignObservation] = []
    checks: list[dict[str, object]] = []
    raw: list[tuple[int, str, str, dict[str, object]]] = []
    for viewport in VIEWPORTS:
        context = browser.new_context(viewport=viewport, color_scheme="light")
        for route in routes:
            page = context.new_page()
            route_path = _next_route(route)
            response = page.goto(f"{base_url.rstrip('/')}{route_path}", wait_until="networkidle", timeout=30_000)
            if response is None or response.status >= 400 or page.locator("main#main h1").count() != 1:
                raise RuntimeError(f"generated candidate route contract failed: {route}")
            metrics = dict(page.evaluate(_METRICS_JS))
            locale = "tr" if route.lstrip("/").startswith("tr/") else "en"
            raw.append((viewport["width"], route, locale, metrics))
            slug = route.strip("/").replace("/", "-") or locale
            shot = screenshots / f"{slug}-{viewport['width']}x{viewport['height']}.png"
            page.screenshot(path=str(shot), full_page=True)
            checks.append({"route": route, "runtime_route": route_path, "viewport": viewport, "status": response.status, "screenshot": shot.relative_to(root).as_posix(), **metrics})
            page.close()
        context.close()
    fingerprint_counts: dict[tuple[int, str, str], int] = {}
    for width, route, locale, metrics in raw:
        page_name = route.rsplit("/", 1)[-1].replace(".html", "")
        if page_name not in {"index", "contact"}:
            key = (width, locale, str(metrics["section_fingerprint"]))
            fingerprint_counts[key] = fingerprint_counts.get(key, 0) + 1
    for width, route, locale, metrics in raw:
        key = (width, locale, str(metrics["section_fingerprint"]))
        repeated = 1 if fingerprint_counts.get(key, 0) > 1 else 0
        rows.append(DesignObservation(route="/" + route.lstrip("/").replace(".html", "").replace("/index", ""), locale=locale, viewport=width, horizontal_overflow=int(metrics["horizontal_overflow"]), clipped_elements=int(metrics["clipped_elements"]), overlapping_elements=int(metrics["overlapping_elements"]), missing_focus_indicators=int(metrics["missing_focus_indicators"]), undersized_touch_targets=int(metrics["undersized_touch_targets"]), contrast_failures=int(metrics["contrast_failures"]), missing_alt_text=int(metrics["missing_alt_text"]), form_label_failures=int(metrics["form_label_failures"]), text_scaling_failures=int(metrics["text_scaling_failures"]), giant_heading_failures=int(metrics["giant_heading_failures"]), empty_visual_placeholders=int(metrics["empty_visual_placeholders"]), excessive_whitespace_regions=int(metrics["excessive_whitespace_regions"]), repeated_layout_failures=repeated, cta_hierarchy_failures=int(metrics["cta_hierarchy_failures"]), turkish_layout_failures=int(metrics["turkish_layout_failures"]), mobile_hierarchy_failures=int(metrics["mobile_hierarchy_failures"]), section_rhythm_failures=int(metrics["section_rhythm_failures"]), missing_brand_asset_failures=int(metrics["missing_brand_asset_failures"]), text_heavy_without_structure=int(metrics["text_heavy_without_structure"])))
    return rows, checks


def _start_server(project_root: Path, port: int) -> subprocess.Popen[str]:
    log = (_artifact_root() / f"next-attempt-{port}.log").open("w", encoding="utf-8")
    process = subprocess.Popen(["npm", "run", "start", "--", "-H", "127.0.0.1", "-p", str(port)], cwd=project_root, stdout=log, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError("generated candidate server exited before readiness")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/en", timeout=1) as response:
                if response.status < 400:
                    return process
        except OSError:
            time.sleep(1)
    process.terminate()
    raise RuntimeError("generated candidate server readiness timed out")


def _build(project_root: Path) -> dict[str, object]:
    if (project_root / ".next").exists():
        shutil.rmtree(project_root / ".next")
    typecheck = subprocess.run(["npm", "run", "typecheck"], cwd=project_root, check=False, capture_output=True, text=True)
    if typecheck.returncode != 0:
        raise RuntimeError("generated candidate typecheck failed\n" + typecheck.stdout + typecheck.stderr)
    build = subprocess.run(["npm", "run", "build"], cwd=project_root, check=False, capture_output=True, text=True)
    if build.returncode != 0:
        raise RuntimeError("generated candidate build failed\n" + build.stdout + build.stderr)
    return {"typecheck": "PASS", "build": "PASS"}


def certify(base_url: str = "http://127.0.0.1:3200") -> int:
    root = _artifact_root()
    manifest = json.loads((root / "trial-manifest.json").read_text(encoding="utf-8"))
    routes = tuple(str(route) for route in manifest.get("routes", []))
    if not routes:
        raise RuntimeError("generated candidate exposed no routes")
    project_root = root / "source-project"
    subprocess.run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=project_root, check=True)
    refinement_log: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        reference_report = _ingest_reference(browser, root)
        final_gate = None
        for attempt in range(1, 4):
            build_result = _build(project_root)
            process = _start_server(project_root, 3200)
            try:
                rows, checks = _collect_attempt(browser, base_url, root, routes, attempt)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
            gate = assess_visual_quality(rows, attempt=attempt)
            final_gate = gate
            metrics_summary = {"max_heading_px": max(float(item.get("max_heading_px", 0)) for item in checks), "max_section_gap_px": max(float(item.get("max_section_gap_px", 0)) for item in checks), "blocking_findings": len(gate.assessment.blocking_findings)}
            attempts.append({"attempt": attempt, "build": build_result, "status": gate.status, "scores": asdict(gate.scores), "thresholds": gate.thresholds, "covered_viewports": gate.assessment.covered_viewports, "covered_locales": gate.assessment.covered_locales, "findings": [asdict(item) for item in gate.assessment.findings], "metrics_summary": metrics_summary, "checks": checks})
            if attempt < 3:
                refinement_log.append(_apply_refinement(project_root, attempt, metrics_summary))
        browser.close()
    if final_gate is None:
        raise RuntimeError("visual quality evaluation did not run")
    evidence = {
        "schema": "ilaios.web-factory.visual-quality.v2",
        "source_sha": manifest.get("source_sha"),
        "engine": "playwright-chromium-next-production",
        "reference_report": "reference-report.json",
        "reference_observation_count": len(reference_report["observations"]),
        "attempts": attempts,
        "refinements": refinement_log,
        "final_status": final_gate.status,
        "accepted": final_gate.accepted,
        "final_scores": asdict(final_gate.scores),
        "thresholds": final_gate.thresholds,
        "final_source_project_digest": _tree_digest(project_root),
        "production_mutation": False,
        "production_publish_requested": False,
    }
    _write_json(root / "visual-quality-evidence.json", evidence)
    _write_json(root / "browser-evidence.json", {"schema": "ilaios.web-factory.corporate-trial-browser.v2", "source_sha": manifest.get("source_sha"), "routes": list(routes), "viewports": list(VIEWPORTS), "attempts": attempts, "browser_pass": final_gate.accepted, "production_mutation": False})
    if not final_gate.accepted:
        print(json.dumps(evidence, sort_keys=True))
        print("ILAIOS_WEB_FACTORY_DESIGN_QUALITY=FAILED")
        return 1
    print(json.dumps(evidence, sort_keys=True))
    print("ILAIOS_WEB_FACTORY_CORPORATE_TRIAL_BROWSER=PASS")
    print("ILAIOS_WEB_FACTORY_DESIGN_QUALITY=PASS")
    return 0


def capture(base_url: str) -> int:
    return certify(base_url)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", metavar="BASE_URL")
    parser.add_argument("--certify", action="store_true")
    args = parser.parse_args()
    if args.capture:
        return capture(args.capture)
    if args.certify:
        return certify()
    return generate()


if __name__ == "__main__":
    raise SystemExit(main())
