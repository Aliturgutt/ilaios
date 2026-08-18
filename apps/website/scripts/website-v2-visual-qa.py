from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("ILAIOS_V2_BASE_URL", "http://127.0.0.1:3100").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("ILAIOS_V2_VISUAL_ARTIFACT_DIR", "artifacts/website-v2-visual-qa"))

ROUTES = (
    ("home", ""),
    ("platform", "/platform"),
    ("factories", "/factories"),
    ("capabilities", "/capabilities"),
    ("security", "/security"),
    ("solutions", "/solutions"),
    ("enterprise", "/enterprise"),
    ("individuals", "/individuals"),
    ("how-it-works", "/how-it-works"),
    ("core", "/core"),
    ("trust", "/trust"),
    ("architecture", "/architecture"),
    ("docs", "/docs"),
    ("resources", "/resources"),
    ("about", "/about"),
    ("contact", "/contact"),
)

VIEWPORTS = (
    ("desktop", 1440, 1000, True),
    ("tablet", 1024, 900, False),
    ("mobile", 390, 844, True),
)


def localized_path(locale: str, route: str) -> str:
    if locale == "en":
        return route or "/"
    return "/tr" + route if route else "/tr"


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
        result["mobile_menu_open"] = True
        result["mobile_menu_overflow_px"] = page.evaluate(
            "document.documentElement.scrollWidth - window.innerWidth"
        )
        toggle.click()
    elif viewport_name == "desktop":
        summary = page.locator(".explore-menu summary")
        if summary.count() == 1 and summary.is_visible():
            summary.click()
            panel = page.locator(".explore-menu-panel")
            if panel.count() != 1 or not panel.is_visible():
                raise RuntimeError("Explore menu did not open")
            box = panel.bounding_box()
            if box is not None and box["x"] + box["width"] > 1441:
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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=False)

        for locale in ("en", "tr"):
            for route_name, route in ROUTES:
                for viewport_name, width, height, take_screenshot in VIEWPORTS:
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

                        h1_box = h1.bounding_box()
                        record["h1_font_px"] = page.evaluate(
                            "el => parseFloat(getComputedStyle(el).fontSize)", h1.element_handle()
                        )
                        record["h1_box"] = h1_box
                        record.update(inspect_navigation(page, viewport_name))

                        if take_screenshot:
                            file_name = f"{locale}__{route_name}__{viewport_name}-{width}x{height}.png"
                            page.screenshot(path=str(screenshots / file_name), full_page=True)
                            record["screenshot"] = f"screenshots/{file_name}"
                        record["result"] = "PASS"
                    except Exception as exc:  # noqa: BLE001 - CI harness must aggregate route failures.
                        record["result"] = "FAIL"
                        record["failure"] = str(exc)
                        failures.append(f"{locale} {path} {viewport_name}: {exc}")
                        failure_name = f"FAIL__{locale}__{route_name}__{viewport_name}-{width}x{height}.png"
                        page.screenshot(path=str(screenshots / failure_name), full_page=True)
                    finally:
                        records.append(record)
                        page.close()

        context.close()
        browser.close()

    report = {
        "schema": "ilaios.website-v2.visual-qa.v1",
        "base_url": BASE_URL,
        "routes": len(ROUTES) * 2,
        "viewports": [name for name, *_ in VIEWPORTS],
        "checks": len(records),
        "screenshots_expected": len(ROUTES) * 2 * 2,
        "failures": failures,
        "status": "FAIL" if failures else "PASS",
        "records": records,
    }
    (ARTIFACT_DIR / "visual-qa.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: report[k] for k in ("status", "routes", "checks", "screenshots_expected", "failures")}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
