from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("ILAIOS_V2_BASE_URL", "http://127.0.0.1:3100").rstrip("/")
ARTIFACT_DIR = Path(
    os.environ.get("ILAIOS_V2_VISUAL_ARTIFACT_DIR", "artifacts/website-v2-visual-qa")
)

ROUTES = (
    ("home", ""),
    ("about", "/about"),
    ("agents", "/agents"),
    ("architecture", "/architecture"),
    ("capabilities", "/capabilities"),
    ("contact", "/contact"),
    ("core", "/core"),
    ("desktop", "/desktop"),
    ("docs", "/docs"),
    ("enterprise", "/enterprise"),
    ("factories", "/factories"),
    ("factory-app", "/factories/app"),
    ("factory-commerce-growth", "/factories/commerce-growth"),
    ("factory-creative-document", "/factories/creative-document"),
    ("factory-personal-operations", "/factories/personal-operations"),
    ("factory-research-data", "/factories/research-data"),
    ("factory-security", "/factories/security"),
    ("factory-software", "/factories/software"),
    ("factory-video", "/factories/video"),
    ("factory-web", "/factories/web"),
    ("how-it-works", "/how-it-works"),
    ("use-ilaios", "/use-ilaios"),
    ("individuals", "/individuals"),
    ("platform", "/platform"),
    ("platform-control-plane", "/platform/control-plane"),
    ("platform-evidence", "/platform/evidence"),
    ("platform-execution", "/platform/execution"),
    ("platform-validation", "/platform/validation"),
    ("privacy", "/privacy"),
    ("resources", "/resources"),
    ("resource-agent-security", "/resources/agent-security-and-governance"),
    ("resource-control-plane", "/resources/control-plane-agent-architecture"),
    ("resource-deterministic", "/resources/deterministic-execution-vs-ai-agents"),
    ("security", "/security"),
    ("security-approvals", "/security/approvals"),
    ("security-audit", "/security/audit"),
    ("security-permissions", "/security/permissions"),
    ("solutions", "/solutions"),
    ("terms", "/terms"),
    ("trust", "/trust"),
    ("updates", "/updates"),
)

SCREENSHOT_ROUTE_NAMES = {
    "home",
    "platform",
    "factories",
    "capabilities",
    "security",
    "solutions",
    "enterprise",
    "individuals",
    "how-it-works",
    "use-ilaios",
    "core",
    "trust",
    "architecture",
    "docs",
    "resources",
    "about",
    "contact",
    "privacy",
}

VIEWPORTS = (("desktop", 1440, 1000), ("tablet", 1024, 900), ("mobile", 390, 844))
DARK_VIEWPORTS = (("desktop", 1440, 1000), ("mobile", 390, 844))


def localized_path(locale: str, route: str) -> str:
    return (route or "/") if locale == "en" else ("/tr" + route if route else "/tr")


def normalized_internal_href(href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlsplit(href)
    base = urlsplit(BASE_URL)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc:
            return None
    path = parsed.path or "/"
    return f"{path}?{parsed.query}" if parsed.query else path


def overflow_elements(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('body *')).map((el) => {
          const r=el.getBoundingClientRect();
          return {tag:el.tagName.toLowerCase(),cls:typeof el.className==='string'?el.className.slice(0,120):'',left:r.left,right:r.right,width:r.width};
        }).filter((x)=>x.width>0&&(x.left<-1||x.right>innerWidth+1)).slice(0,20)"""
    )


def visible_chromatic_ui(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        r"""() => {
          const parse=(v)=>{const m=String(v||'').match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);return m?[+m[1],+m[2],+m[3]]:null;};
          const chroma=(rgb)=>{if(!rgb)return false;const [r,g,b]=rgb,max=Math.max(r,g,b),min=Math.min(r,g,b);if(max-min<20)return false;return (b>r+24&&b>g+8)||(g>r+28&&b>r+28);};
          return Array.from(document.querySelectorAll('body *')).filter((el)=>{
            const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&!el.closest('.brand');
          }).map((el)=>{const s=getComputedStyle(el),values=[s.color,s.backgroundColor,s.borderTopColor,s.borderRightColor,s.borderBottomColor,s.borderLeftColor];return {tag:el.tagName.toLowerCase(),cls:typeof el.className==='string'?el.className.slice(0,120):'',values,bad:values.some((v)=>chroma(parse(v)))};}).filter((x)=>x.bad).slice(0,20);
        }"""
    )


def header_geometry(page: Page) -> dict[str, object]:
    return page.evaluate(
        """() => {const el=document.querySelector('.site-header .brand');if(!el)return {brand:null};const r=el.getBoundingClientRect();return {brand:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]};}"""
    )


def inspect_navigation(page: Page, viewport_name: str, width: int) -> dict[str, object]:
    brand = page.locator(".site-header .brand")
    nav = page.locator(".site-header .nav-panel")
    toggle = page.locator(".site-header .menu-toggle")
    if brand.count() != 1 or not brand.is_visible():
        raise RuntimeError("header brand is missing or hidden")
    if nav.count() != 1 or toggle.count() != 1:
        raise RuntimeError("shared navigation controls are missing")

    if viewport_name == "mobile":
        if not toggle.is_visible():
            raise RuntimeError("mobile menu toggle is hidden")
        toggle.click()
        if not nav.is_visible():
            raise RuntimeError("mobile navigation panel did not open")
        box = nav.bounding_box()
        if box is None:
            raise RuntimeError("mobile navigation panel has no geometry")
        if box["width"] > 322:
            raise RuntimeError(f"mobile navigation panel is too wide: {box['width']}px")
        if box["x"] < width - box["width"] - 24:
            raise RuntimeError(
                f"mobile navigation panel is not right anchored: "
                f"x={box['x']} width={box['width']}"
            )
        if not page.locator(".site-header .theme-toggle").is_visible():
            raise RuntimeError("mobile theme control is hidden")
        if not page.locator(".site-header .language-switch").is_visible():
            raise RuntimeError("mobile language control is hidden")
        page.keyboard.press("Escape")
        if nav.is_visible():
            raise RuntimeError("mobile navigation panel did not close on Escape")
        return {
            "mobile_navigation_width": box["width"],
            "mobile_navigation_x": box["x"],
        }

    if not nav.is_visible():
        raise RuntimeError("desktop navigation panel is hidden")
    return {"desktop_navigation": True}


def inspect_footer_hover(page: Page, theme: str) -> dict[str, object]:
    link = page.locator(".site-footer a").first
    if link.count() != 1 or not link.is_visible():
        return {}
    link.hover()
    color = link.evaluate("el => getComputedStyle(el).color")
    if theme == "light" and color in {
        "rgb(255, 255, 255)",
        "rgba(255, 255, 255, 1)",
    }:
        raise RuntimeError("light footer hover text resolves to white")
    return {"footer_hover_color": color}


def inspect_contact(page: Page, locale: str, viewport_name: str) -> dict[str, object]:
    text = page.locator("main#main-content").inner_text().lower()
    forbidden = "kamu" if locale == "tr" else "verified public route"
    if forbidden in text:
        raise RuntimeError(f"contact copy still exposes removed wording: {forbidden}")
    h1 = page.locator(".contact-intro h1")
    if h1.count() != 1 or not h1.is_visible():
        raise RuntimeError("contact H1 missing")
    size = float(h1.evaluate("el => parseFloat(getComputedStyle(el).fontSize)"))
    if viewport_name == "desktop" and size > 62:
        raise RuntimeError(f"contact H1 remains oversized: {size}px")
    intro = page.locator(".contact-intro").bounding_box()
    directory = page.locator(".contact-directory").bounding_box()
    if intro and directory:
        gap = directory["y"] - (intro["y"] + intro["height"])
        if gap > 100:
            raise RuntimeError(f"contact hero-directory dead space too large: {gap}px")
    return {"contact_h1_px": size}


def run_page_checks(
    page: Page,
    *,
    locale: str,
    route_name: str,
    path: str,
    viewport_name: str,
    width: int,
    height: int,
    theme: str,
    internal_links: set[str],
    header_baselines: dict[str, dict[str, object]],
) -> dict[str, object]:
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=45_000)
    status = response.status if response is not None else 0
    actual_theme = page.evaluate("document.documentElement.dataset.theme")
    h1 = page.locator("main#main-content h1")
    overflow = float(page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
    offenders = overflow_elements(page) if overflow > 1 else []
    chromatic_ui = visible_chromatic_ui(page)
    broken_images = page.locator("img").evaluate_all(
        """els => els.filter((el)=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0&&(!el.complete||el.naturalWidth===0||el.naturalHeight===0);}).map((el)=>({src:el.currentSrc||el.src,alt:el.alt||''})).slice(0,20)"""
    )

    if status >= 400 or status == 0:
        raise RuntimeError(f"HTTP {status}")
    if actual_theme != theme:
        raise RuntimeError(f"theme mismatch: expected {theme}, got {actual_theme}")
    if h1.count() != 1 or not h1.is_visible():
        raise RuntimeError("exactly one visible main H1 is required")
    if overflow > 1:
        raise RuntimeError(f"horizontal overflow {overflow}px")
    if console_errors:
        raise RuntimeError(f"console errors: {console_errors[:3]}")
    if page_errors:
        raise RuntimeError(f"page errors: {page_errors[:3]}")
    if broken_images:
        raise RuntimeError(f"broken images: {broken_images[:3]}")
    if chromatic_ui:
        raise RuntimeError(f"chromatic UI outside canonical assets: {chromatic_ui[:3]}")

    if route_name == "home":
        if page.locator('[data-visual-role="homepage-v2-authoritative"]').count() != 1:
            raise RuntimeError("authoritative homepage V2 marker missing")
        if page.locator(".v2-recovery-home").count() != 0:
            raise RuntimeError("legacy WebsiteV2HomeRecovery is still rendered")

    record: dict[str, object] = {
        "locale": locale,
        "route": path,
        "route_name": route_name,
        "viewport": viewport_name,
        "width": width,
        "height": height,
        "theme": theme,
        "status": status,
        "horizontal_overflow_px": overflow,
        "overflow_elements": offenders,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "broken_images": broken_images,
        "chromatic_ui": chromatic_ui,
        "h1_font_px": page.evaluate(
            "el => parseFloat(getComputedStyle(el).fontSize)", h1.element_handle()
        ),
        "h1_box": h1.bounding_box(),
    }
    record.update(inspect_navigation(page, viewport_name, width))
    record.update(inspect_footer_hover(page, theme))
    if route_name == "contact":
        record.update(inspect_contact(page, locale, viewport_name))

    if viewport_name == "desktop":
        geometry = header_geometry(page)
        baseline_key = f"{theme}:{locale}"
        baseline = header_baselines.setdefault(baseline_key, geometry)
        if geometry != baseline:
            raise RuntimeError(
                f"header geometry drift for {baseline_key}: "
                f"expected {baseline}, got {geometry}"
            )
        record["header_geometry"] = geometry
        hrefs = page.locator("a[href]").evaluate_all(
            "els => els.map((el)=>el.getAttribute('href')).filter(Boolean)"
        )
        for href in hrefs:
            normalized = normalized_internal_href(str(href))
            if normalized is not None:
                internal_links.add(normalized)
    return record


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = ARTIFACT_DIR / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    failures: list[str] = []
    internal_links: set[str] = set()
    internal_link_results: list[dict[str, object]] = []
    header_baselines: dict[str, dict[str, object]] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=False)

        for locale in ("en", "tr"):
            for route_name, route in ROUTES:
                for viewport_name, width, height in VIEWPORTS:
                    path = localized_path(locale, route)
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": height})
                    page.add_init_script("localStorage.removeItem('ilaios-theme')")
                    try:
                        record = run_page_checks(
                            page,
                            locale=locale,
                            route_name=route_name,
                            path=path,
                            viewport_name=viewport_name,
                            width=width,
                            height=height,
                            theme="light",
                            internal_links=internal_links,
                            header_baselines=header_baselines,
                        )
                        if (
                            route_name in SCREENSHOT_ROUTE_NAMES
                            and viewport_name in {"desktop", "mobile"}
                        ):
                            name = (
                                f"light__{locale}__{route_name}__"
                                f"{viewport_name}-{width}x{height}.png"
                            )
                            page.screenshot(path=str(screenshots / name), full_page=True)
                            record["screenshot"] = f"screenshots/{name}"
                        record["result"] = "PASS"
                    except Exception as exc:  # noqa: BLE001
                        record = {
                            "locale": locale,
                            "route": path,
                            "route_name": route_name,
                            "viewport": viewport_name,
                            "width": width,
                            "height": height,
                            "theme": "light",
                            "result": "FAIL",
                            "failure": str(exc),
                        }
                        failures.append(
                            f"light {locale} {path} {viewport_name}: {exc}"
                        )
                        page.screenshot(
                            path=str(
                                screenshots
                                / (
                                    f"FAIL__light__{locale}__{route_name}__"
                                    f"{viewport_name}-{width}x{height}.png"
                                )
                            ),
                            full_page=True,
                        )
                    finally:
                        records.append(record)
                        page.close()

        for locale in ("en", "tr"):
            for route_name, route in ROUTES:
                for viewport_name, width, height in DARK_VIEWPORTS:
                    path = localized_path(locale, route)
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": height})
                    page.add_init_script("localStorage.setItem('ilaios-theme', 'dark')")
                    try:
                        record = run_page_checks(
                            page,
                            locale=locale,
                            route_name=route_name,
                            path=path,
                            viewport_name=viewport_name,
                            width=width,
                            height=height,
                            theme="dark",
                            internal_links=internal_links,
                            header_baselines=header_baselines,
                        )
                        if route_name in SCREENSHOT_ROUTE_NAMES:
                            name = (
                                f"dark__{locale}__{route_name}__"
                                f"{viewport_name}-{width}x{height}.png"
                            )
                            page.screenshot(path=str(screenshots / name), full_page=True)
                            record["screenshot"] = f"screenshots/{name}"
                        record["result"] = "PASS"
                    except Exception as exc:  # noqa: BLE001
                        record = {
                            "locale": locale,
                            "route": path,
                            "route_name": route_name,
                            "viewport": viewport_name,
                            "width": width,
                            "height": height,
                            "theme": "dark",
                            "result": "FAIL",
                            "failure": str(exc),
                        }
                        failures.append(
                            f"dark {locale} {path} {viewport_name}: {exc}"
                        )
                        page.screenshot(
                            path=str(
                                screenshots
                                / (
                                    f"FAIL__dark__{locale}__{route_name}__"
                                    f"{viewport_name}-{width}x{height}.png"
                                )
                            ),
                            full_page=True,
                        )
                    finally:
                        records.append(record)
                        page.close()

        for target in sorted(internal_links):
            response = context.request.get(
                f"{BASE_URL}{target}",
                timeout=30_000,
                max_redirects=5,
            )
            status = response.status
            ok = status < 400
            internal_link_results.append(
                {
                    "target": target,
                    "status": status,
                    "result": "PASS" if ok else "FAIL",
                }
            )
            if not ok:
                failures.append(f"internal link {target}: HTTP {status}")

        context.close()
        browser.close()

    report = {
        "schema": "ilaios.website-v2.visual-qa.v5",
        "base_url": BASE_URL,
        "public_route_pairs": len(ROUTES),
        "localized_routes": len(ROUTES) * 2,
        "light_viewports": [name for name, *_ in VIEWPORTS],
        "dark_viewports": [name for name, *_ in DARK_VIEWPORTS],
        "checks": len(records),
        "internal_link_targets": len(internal_link_results),
        "internal_link_results": internal_link_results,
        "header_baselines": header_baselines,
        "failures": failures,
        "status": "FAIL" if failures else "PASS",
        "records": records,
    }
    (ARTIFACT_DIR / "visual-qa.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "public_route_pairs",
                    "localized_routes",
                    "checks",
                    "internal_link_targets",
                    "failures",
                )
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
