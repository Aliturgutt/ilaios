from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from services.integrations.web_factory import GovernedWebFactory, derive_website_spec
from services.integrations.web_project import materialize_next_project
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


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

VIEWPORTS = (
    {"width": 390, "height": 844},
    {"width": 1440, "height": 900},
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


def _artifact_root() -> Path:
    value = os.environ.get(
        "ILAIOS_WEB_FACTORY_TRIAL_ARTIFACT_DIR",
        "artifacts/web-factory-ilaios-trial",
    )
    return Path(value).resolve()


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _apply_trial_responsive_guard(project_root: Path) -> dict[str, object]:
    css_path = project_root / "app" / "globals.css"
    css = css_path.read_text(encoding="utf-8")
    if _MOBILE_GRID_768_FROM not in css or _MOBILE_GRID_430_FROM not in css:
        raise RuntimeError("generated Web responsive grid contract changed unexpectedly")
    patched = css.replace(_MOBILE_GRID_768_FROM, _MOBILE_GRID_768_TO, 1)
    patched = patched.replace(_MOBILE_GRID_430_FROM, _MOBILE_GRID_430_TO, 1)
    if patched == css:
        raise RuntimeError("generated Web responsive grid guard made no change")
    css_path.write_text(patched, encoding="utf-8")
    return {
        "applied": True,
        "scope": "generated-candidate-only",
        "reason": "composition-specific context grids must honor 768px/430px mobile collapse",
        "production_mutation": False,
    }


def generate() -> int:
    root = _artifact_root()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    request_id = "ilaios-corporate-web-factory-trial-20260909"
    spec = derive_website_spec(request_id, OBJECTIVE)
    now = datetime.now(timezone.utc)
    grant = ExecutionGrant(
        "ilaios-corporate-web-factory-trial-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({spec.site_id}),
        now + timedelta(minutes=10),
        BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )
    factory = GovernedWebFactory(GrantPolicy(), root / "generated-bundles")
    acceptance = factory.build_generated_site(spec, grant=grant, now=now)
    if not acceptance.accepted or acceptance.design_strategy is None:
        raise RuntimeError("Web Factory did not accept the generated ILAIOS candidate")
    if acceptance.qa is None or acceptance.qa.get("passed") is not True:
        raise RuntimeError("Web Factory QA did not pass for the generated ILAIOS candidate")

    project = materialize_next_project(
        spec,
        acceptance.design_strategy,
        root / "materialized-projects",
    )
    source = Path(project.root_path)
    destination = root / "source-project"
    shutil.copytree(source, destination)
    responsive_guard = _apply_trial_responsive_guard(destination)
    candidate_digest = _tree_digest(destination)

    source_sha = os.environ.get("ILAIOS_SOURCE_SHA", os.environ.get("GITHUB_SHA", "UNBOUND"))
    manifest = {
        "schema": "ilaios.web-factory.corporate-trial.v1",
        "source_sha": source_sha,
        "request_id": request_id,
        "reference_site": "https://www.ilaios.com",
        "reference_mode": "PRODUCT_TRUTH_AND_BRAND_ONLY",
        "objective": OBJECTIVE,
        "spec": spec.to_dict(),
        "design_strategy": acceptance.design_strategy,
        "factory_accepted": acceptance.accepted,
        "factory_qa": acceptance.qa,
        "routes": list(acceptance.routes),
        "factory_materialization_digest": project.digest,
        "source_project_digest": candidate_digest,
        "source_project_id": project.project_id,
        "source_project_path": "source-project",
        "trial_responsive_guard": responsive_guard,
        "production_mutation": False,
        "production_publish_requested": False,
    }
    (root / "trial-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
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


def capture(base_url: str) -> int:
    root = _artifact_root()
    manifest_path = root / "trial-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("trial manifest is missing; generation must run first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    routes = tuple(str(route) for route in manifest.get("routes", []))
    if not routes:
        raise RuntimeError("generated candidate exposed no routes")

    screenshots = root / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=False)
        for viewport in VIEWPORTS:
            for route in routes:
                page = context.new_page()
                page.set_viewport_size(viewport)
                route_path = _next_route(route)
                response = page.goto(
                    f"{base_url.rstrip('/')}{route_path}",
                    wait_until="networkidle",
                    timeout=30_000,
                )
                if response is None or response.status >= 400:
                    raise RuntimeError(f"generated candidate route failed: {route}")
                if page.locator("main#main h1").count() != 1:
                    raise RuntimeError(f"generated candidate H1 contract failed: {route}")
                overflow = float(
                    page.evaluate(
                        "document.documentElement.scrollWidth - "
                        "document.documentElement.clientWidth"
                    )
                )
                if overflow > 1:
                    raise RuntimeError(
                        f"generated candidate horizontal overflow: {route} {viewport} {overflow}"
                    )
                locale = "tr" if route.lstrip("/").startswith("tr/") else "en"
                slug = route.strip("/").replace("/", "-") or locale
                page.screenshot(
                    path=str(
                        screenshots
                        / f"{slug}-{viewport['width']}x{viewport['height']}.png"
                    ),
                    full_page=True,
                )
                checks.append(
                    {
                        "route": route,
                        "runtime_route": route_path,
                        "viewport": viewport,
                        "status": response.status,
                        "horizontal_overflow_px": overflow,
                    }
                )
                page.close()
        context.close()
        browser.close()

    evidence = {
        "schema": "ilaios.web-factory.corporate-trial-browser.v1",
        "source_sha": manifest.get("source_sha"),
        "engine": "playwright-chromium-next-production",
        "routes": list(routes),
        "viewports": list(VIEWPORTS),
        "checks": checks,
        "browser_pass": True,
        "production_mutation": False,
    }
    (root / "browser-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, sort_keys=True))
    print("ILAIOS_WEB_FACTORY_CORPORATE_TRIAL_BROWSER=PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", metavar="BASE_URL")
    args = parser.parse_args()
    if args.capture:
        return capture(args.capture)
    return generate()


if __name__ == "__main__":
    raise SystemExit(main())
