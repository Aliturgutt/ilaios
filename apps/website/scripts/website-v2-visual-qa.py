from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("ILAIOS_V2_BASE_URL", "http://127.0.0.1:3100").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("ILAIOS_V2_VISUAL_ARTIFACT_DIR", "artifacts/website-v2-visual-qa"))

# Every public EN route has a /tr counterpart. API, robots, sitemap and _not-found
# are intentionally excluded because this harness certifies user-facing pages.
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

# Keep artifact size bounded while still preserving visual evidence for the
# primary product, governance and company surfaces. Every route is still tested.
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
}

VIEWPORTS = (
    ("desktop", 1440, 1000),
    ("tablet", 1024, 900),
    ("mobile", 390, 844),
)


def localized_path(locale: str, route: str) -> str:
    if locale == "en":
        return route or "/"
    return "/tr" + route if route else "/tr"


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
    if not path.startswith("/"):
        return None
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path


def overflow_elements(page: Page) -> list[dict[str, object]]:
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('body *'))
          .map((el) => {
            const r = el.getBoundingClientRect();
            return {
              tag: el.tagName.toLowerCase(),
              cls: typeof el.className === 'string' ? el.className.slice(0, 120) : '',
              left: Math.round(r.left * 10) / 10,
              right: Math.round(r.right * 10) / 10,
              width: Math.round(r.width * 10) / 10,
            };
          })
          .filter((x) => x.width > 0 && (x.left < -1 || x.right > window.innerWidth + 1))
          .slice(0, 20)
        """
    )


def inspect_navigation(page: Page, viewport_name: str) -> dict[str, object]:
    result: dict[str, object] = {}
    if viewport_name == "mobile":
        toggle = page.locator(".menu-toggle")
        if toggle.count() != 1 or not toggle.is_visible():
            raise RuntimeError("mobile menu toggle is missing or hidden")
        toggle.click()
        panel = page.locator(".nav-panel")
        if panel.count() != 1 or not panel.is_visible():
            raise RuntimeError("mobile navigation panel did not open")
        menu_overflow = float(page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
        if menu_overflow > 1:
            raise RuntimeError(f"mobile navigation creates horizontal overflow {menu_overflow}px")
        result["mobile_menu_open"] = True
        result["mobile_menu_overflow_px"] = menu_overflow
        toggle.click()
    elif viewport_name == "desktop":
        summary = page.locator(".explore-menu summary")
        if summary.count() == 1 and summary.is_visible():
            summary.click()
            panel = page.locator(".explore-menu-panel")
            if panel.count() != 1 or not panel.is_visible():
                raise RuntimeError("Explore menu did not open")
            box = panel.bounding_box()
            if box is not None and (box["x"] < -1 or box["x"] + box["width"] > 1441):
                raise RuntimeError("Explore menu is clipped outside the desktop viewport")
            result["explore_menu_open"] = True
            summary.click()
    return result


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = ARTIFACT_DIR / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    failures: list[str] = []
    internal_links: set[str] = set()
    internal_link_results: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=False)

        for locale in ("en", "tr"):
            for route_name, route in ROUTES:
                for viewport_name, width, height in VIEWPORTS:
                    path = localized_path(locale, route)
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": height})
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    page.on(
                        "console",
                        lambda message, errors=console_errors: errors.append(message.text)
                        if message.type == "error"
                        else None,
                    )
                    page.on("pageerror", lambda error, errors=page_errors: errors.append(str(error)))

                    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=45_000)
                    status = response.status if response is not None else 0
                    h1 = page.locator("main#main-content h1")
                    overflow = float(page.evaluate("document.documentElement.scrollWidth - window.innerWidth"))
                    offenders = overflow_elements(page) if overflow > 1 else []
                    broken_images = page.locator("img").evaluate_all(
                        """els => els
                          .filter((el) => {
                            const s = getComputedStyle(el);
                            const r = el.getBoundingClientRect();
                            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0 &&
                              (!el.complete || el.naturalWidth === 0 || el.naturalHeight === 0);
                          })
                          .map((el) => ({src: el.currentSrc || el.src, alt: el.alt || ''}))
                          .slice(0, 20)"""
                    )
                    record: dict[str, object] = {
                        "locale": locale,
                        "route": path,
                        "route_name": route_name,
                        "viewport": viewport_name,
                        "width": width,
                        "height": height,
                        "status": status,
                        "horizontal_overflow_px": overflow,
                        "overflow_elements": offenders,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "broken_images": broken_images,
                    }

                    try:
                        if status >= 400 or status == 0:
                            raise RuntimeError(f"HTTP {status}")
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
                        if route_name == "home":
                            authoritative = page.locator('[data-visual-role="homepage-v2-authoritative"]')
                            legacy = page.locator('.v2-recovery-home')
                            if authoritative.count() != 1 or not authoritative.is_visible():
                                raise RuntimeError("authoritative homepage V2 marker missing")
                            if legacy.count() != 0:
                                raise RuntimeError("legacy WebsiteV2HomeRecovery is still rendered")

                        record["h1_font_px"] = page.evaluate(
                            "el => parseFloat(getComputedStyle(el).fontSize)", h1.element_handle()
                        )
                        record["h1_box"] = h1.bounding_box()
                        record.update(inspect_navigation(page, viewport_name))

                        if viewport_name == "desktop":
                            hrefs = page.locator("a[href]").evaluate_all(
                                "els => els.map((el) => el.getAttribute('href')).filter(Boolean)"
                            )
                            for href in hrefs:
                                normalized = normalized_internal_href(str(href))
                                if normalized is not None:
                                    internal_links.add(normalized)

                        if route_name in SCREENSHOT_ROUTE_NAMES and viewport_name in {"desktop", "mobile"}:
                            file_name = f"{locale}__{route_name}__{viewport_name}-{width}x{height}.png"
                            page.screenshot(path=str(screenshots / file_name), full_page=True)
                            record["screenshot"] = f"screenshots/{file_name}"
                        record["result"] = "PASS"
                    except Exception as exc:  # noqa: BLE001 - aggregate all rendered route failures.
                        record["result"] = "FAIL"
                        record["failure"] = str(exc)
                        failures.append(f"{locale} {path} {viewport_name}: {exc}")
                        failure_name = f"FAIL__{locale}__{route_name}__{viewport_name}-{width}x{height}.png"
                        page.screenshot(path=str(screenshots / failure_name), full_page=True)
                    finally:
                        records.append(record)
                        page.close()

        for target in sorted(internal_links):
            response = context.request.get(f"{BASE_URL}{target}", timeout=30_000, max_redirects=5)
            status = response.status
            ok = status < 400
            internal_link_results.append({"target": target, "status": status, "result": "PASS" if ok else "FAIL"})
            if not ok:
                failures.append(f"internal link {target}: HTTP {status}")

        # Explicitly certify both Light and Dark homepage themes. The default
        # browser color scheme is not evidence for the alternate theme.
        for theme in ("light", "dark"):
            for locale in ("en", "tr"):
                for viewport_name, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844)):
                    path = localized_path(locale, "")
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": height})
                    page.add_init_script(
                        f"localStorage.setItem('ilaios-theme', '{theme}')"
                    )
                    try:
                        response = page.goto(
                            f"{BASE_URL}{path}", wait_until="networkidle", timeout=45_000
                        )
                        if response is None or response.status >= 400:
                            raise RuntimeError(f"HTTP {response.status if response else 0}")
                        actual_theme = page.evaluate("document.documentElement.dataset.theme")
                        if actual_theme != theme:
                            raise RuntimeError(
                                f"theme bootstrap mismatch: expected {theme}, got {actual_theme}"
                            )
                        contrast = float(
                            page.evaluate(
                                """() => {
                                  const parse = (value) => {
                                    const m = value.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                                    return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
                                  };
                                  const lum = (rgb) => {
                                    const c = rgb.map(v => {
                                      const s = v / 255;
                                      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
                                    });
                                    return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
                                  };
                                  const h1 = document.querySelector('.homepage-v2 h1');
                                  const host = document.querySelector('.homepage-v2');
                                  if (!h1 || !host) return 0;
                                  const fg = parse(getComputedStyle(h1).color);
                                  const bg = parse(getComputedStyle(host).backgroundColor) ||
                                             parse(getComputedStyle(document.body).backgroundColor);
                                  if (!fg || !bg) return 0;
                                  const l1 = lum(fg), l2 = lum(bg);
                                  return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
                                }"""
                            )
                        )
                        if contrast < 4.5:
                            raise RuntimeError(
                                f"{theme} homepage H1 contrast too low: {contrast:.2f}"
                            )
                        gradients = page.locator(".homepage-v2 *").evaluate_all(
                            """els => els.filter((el) =>
                              (getComputedStyle(el).backgroundImage || '').includes('gradient(')
                            ).length"""
                        )
                        if gradients:
                            raise RuntimeError(
                                f"{theme} homepage contains {gradients} decorative gradients"
                            )
                        file_name = (
                            f"theme__{theme}__{locale}__home__{viewport_name}-{width}x{height}.png"
                        )
                        page.screenshot(path=str(screenshots / file_name), full_page=True)
                        records.append(
                            {
                                "locale": locale,
                                "route": path,
                                "route_name": "home-theme",
                                "viewport": viewport_name,
                                "width": width,
                                "height": height,
                                "theme": theme,
                                "h1_contrast": contrast,
                                "screenshot": f"screenshots/{file_name}",
                                "result": "PASS",
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        failures.append(
                            f"{locale} {path} {theme} {viewport_name}: {exc}"
                        )
                        records.append(
                            {
                                "locale": locale,
                                "route": path,
                                "route_name": "home-theme",
                                "viewport": viewport_name,
                                "width": width,
                                "height": height,
                                "theme": theme,
                                "result": "FAIL",
                                "failure": str(exc),
                            }
                        )
                    finally:
                        page.close()

        context.close()
        browser.close()

    report = {
        "schema": "ilaios.website-v2.visual-qa.v3",
        "base_url": BASE_URL,
        "public_route_pairs": len(ROUTES),
        "localized_routes": len(ROUTES) * 2,
        "viewports": [name for name, *_ in VIEWPORTS],
        "checks": len(records),
        "internal_link_targets": len(internal_link_results),
        "internal_link_results": internal_link_results,
        "screenshots_expected": len(SCREENSHOT_ROUTE_NAMES) * 2 * 2 + 8,
        "failures": failures,
        "status": "FAIL" if failures else "PASS",
        "records": records,
    }
    (ARTIFACT_DIR / "visual-qa.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "public_route_pairs",
                    "localized_routes",
                    "checks",
                    "internal_link_targets",
                    "screenshots_expected",
                    "failures",
                )
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
