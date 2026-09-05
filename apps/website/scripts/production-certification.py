from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Response, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "https://ilaios.com").rstrip("/")
WWW_URL = os.environ.get("WWW_URL", "https://www.ilaios.com").rstrip("/")
EXPECTED_SHA = os.environ.get("EXPECTED_SHA", "").strip()
WAIT_SECONDS = int(os.environ.get("CERTIFICATION_WAIT_SECONDS", "900"))
ARTIFACT_DIR = Path(os.environ.get("CERTIFICATION_ARTIFACT_DIR", "artifacts/production-certification"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

ALL_ROUTE_VIEWPORTS = [(390, 844), (1440, 900)]
CRITICAL_EXTRA_VIEWPORTS = [(320, 780), (360, 800), (430, 932), (768, 1024), (1024, 900)]
CRITICAL_PATHS = {
    "/", "/tr", "/factories", "/tr/factories", "/capabilities", "/tr/capabilities",
    "/security", "/tr/security", "/contact", "/tr/contact",
}
ALLOWED_PROJECT_PRODUCTION_URLS = {"ilaios.com", "www.ilaios.com", "ilaios.vercel.app"}


@dataclass
class BrowserCheck:
    url: str
    final_url: str
    viewport: str
    status: int
    title: str
    lang: str
    canonical: str | None
    overflow_px: int
    x_vercel_id: str | None
    console_errors: list[str]
    page_errors: list[str]
    failed_same_origin_requests: list[str]
    cancelled_rsc_prefetches: list[str]


def http_get(url: str, *, timeout: int = 30) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "ILAIOS-Production-Certification/1.0",
        "Cache-Control": "no-cache", "Pragma": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()


def wait_for_exact_release() -> dict[str, Any]:
    if not EXPECTED_SHA:
        raise RuntimeError("EXPECTED_SHA is required")
    deadline = time.monotonic() + WAIT_SECONDS
    last_error = "release endpoint not checked"
    release_url = f"{BASE_URL}/api/release"
    while time.monotonic() < deadline:
        try:
            status, headers, body = http_get(f"{release_url}?cert={int(time.time())}")
            payload = json.loads(body.decode("utf-8"))
            observed_sha = payload.get("commitSha")
            environment = payload.get("environment")
            deployment_id = payload.get("deploymentId")
            production_url = payload.get("productionUrl")
            if status == 200 and observed_sha == EXPECTED_SHA and environment == "production":
                if deployment_id and not str(deployment_id).startswith("dpl_"):
                    raise RuntimeError(f"Unexpected Vercel deployment id: {deployment_id}")
                if production_url and production_url not in ALLOWED_PROJECT_PRODUCTION_URLS:
                    raise RuntimeError(f"Unexpected production URL: {production_url}")
                payload["releaseEndpointHeaders"] = {
                    "x-vercel-id": headers.get("x-vercel-id"), "server": headers.get("server"),
                    "cache-control": headers.get("cache-control"),
                }
                return payload
            last_error = f"release mismatch status={status} sha={observed_sha!r} environment={environment!r} expected={EXPECTED_SHA!r}"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = str(exc)
        print(f"Waiting for exact production release: {last_error}", flush=True)
        time.sleep(15)
    raise RuntimeError(f"Exact production release did not appear within {WAIT_SECONDS}s: {last_error}")


def load_sitemap() -> list[str]:
    status, _, body = http_get(f"{BASE_URL}/sitemap.xml")
    if status != 200:
        raise RuntimeError(f"sitemap.xml returned HTTP {status}")
    root = ET.fromstring(body)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls: list[str] = []
    for loc in root.findall(f".//{namespace}loc"):
        if not loc.text:
            continue
        parsed = urllib.parse.urlparse(loc.text.strip())
        if parsed.hostname not in {"ilaios.com", "www.ilaios.com"}:
            raise RuntimeError(f"Sitemap contains unexpected host: {loc.text.strip()}")
        urls.append(urllib.parse.urlunparse(("https", "ilaios.com", parsed.path or "/", "", parsed.query, "")))
    if not urls:
        raise RuntimeError("sitemap.xml contains no URLs")
    return sorted(set(urls))


def validate_robots() -> None:
    status, _, body = http_get(f"{BASE_URL}/robots.txt")
    text = body.decode("utf-8", errors="replace")
    if status != 200:
        raise RuntimeError(f"robots.txt returned HTTP {status}")
    if "sitemap" not in text.lower() or "ilaios.com/sitemap.xml" not in text.lower():
        raise RuntimeError("robots.txt does not advertise the canonical sitemap")


def route_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.path or "/"


def is_cancelled_rsc_prefetch(url: str, failure: object) -> bool:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    return "_rsc" in query and "ERR_ABORTED" in str(failure)


def check_page(page: Page, url: str, width: int, height: int) -> BrowserCheck:
    page.set_viewport_size({"width": width, "height": height})
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    cancelled_rsc_prefetches: list[str] = []

    def on_console(message: Any) -> None:
        if message.type == "error": console_errors.append(message.text)
    def on_page_error(error: Any) -> None:
        page_errors.append(str(error))
    def on_request_failed(request: Any) -> None:
        parsed = urllib.parse.urlparse(request.url)
        if parsed.hostname in {"ilaios.com", "www.ilaios.com"}:
            failure = request.failure
            rendered = f"{request.method} {request.url}: {failure}"
            if is_cancelled_rsc_prefetch(request.url, failure):
                cancelled_rsc_prefetches.append(rendered); return
            request_failures.append(rendered)

    page.on("console", on_console); page.on("pageerror", on_page_error); page.on("requestfailed", on_request_failed)
    response: Response | None = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(250)
    if response is None: raise RuntimeError(f"No navigation response for {url}")
    status = response.status
    if status >= 400: raise RuntimeError(f"HTTP {status} for {url}")
    final_url = page.url
    final_host = urllib.parse.urlparse(final_url).hostname
    if final_host not in {"ilaios.com", "www.ilaios.com"}: raise RuntimeError(f"Unexpected final host for {url}: {final_url}")
    title = page.title().strip()
    if not title: raise RuntimeError(f"Missing document title for {url}")
    if page.locator("main").count() < 1: raise RuntimeError(f"Missing <main> for {url}")
    lang = str(page.locator("html").get_attribute("lang") or "")
    expected_lang = "tr" if route_path(url) == "/tr" or route_path(url).startswith("/tr/") else "en"
    if lang != expected_lang: raise RuntimeError(f"Unexpected html lang for {url}: {lang!r}, expected {expected_lang!r}")
    canonical = page.locator('link[rel="canonical"]').get_attribute("href")
    if not canonical: raise RuntimeError(f"Missing canonical URL for {url}")
    if urllib.parse.urlparse(canonical).hostname != "ilaios.com": raise RuntimeError(f"Unexpected canonical host for {url}: {canonical}")
    overflow_px = int(page.evaluate("Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"))
    if overflow_px > 1: raise RuntimeError(f"Horizontal overflow ({overflow_px}px) for {url} at {width}x{height}")
    if console_errors: raise RuntimeError(f"Console errors for {url} at {width}x{height}: {console_errors}")
    if page_errors: raise RuntimeError(f"Page errors for {url} at {width}x{height}: {page_errors}")
    if request_failures: raise RuntimeError(f"Failed same-origin requests for {url} at {width}x{height}: {request_failures}")

    headers = {k.lower(): v for k, v in response.headers.items()}
    result = BrowserCheck(
        url=url, final_url=final_url, viewport=f"{width}x{height}", status=status, title=title,
        lang=lang, canonical=canonical, overflow_px=overflow_px, x_vercel_id=headers.get("x-vercel-id"),
        console_errors=console_errors, page_errors=page_errors, failed_same_origin_requests=request_failures,
        cancelled_rsc_prefetches=cancelled_rsc_prefetches,
    )
    page.remove_listener("console", on_console); page.remove_listener("pageerror", on_page_error); page.remove_listener("requestfailed", on_request_failed)
    return result


def check_minimal_header(page: Page, path: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(200)
    brand = page.locator(".site-header .brand")
    if brand.count() != 1 or not brand.is_visible():
        raise RuntimeError(f"Minimal header brand not visible on {path}")
    if page.locator(".site-header .menu-toggle,.site-header .nav-panel,.site-header .theme-toggle,.site-header .language-switch").count() != 0:
        raise RuntimeError(f"Removed top navigation is still rendered on {path}")


def check_www_alias(page: Page) -> dict[str, Any]:
    page.set_viewport_size({"width": 390, "height": 844})
    response = page.goto(WWW_URL, wait_until="domcontentloaded", timeout=30_000)
    if response is None or response.status >= 400:
        raise RuntimeError(f"www alias failed: {None if response is None else response.status}")
    final_host = urllib.parse.urlparse(page.url).hostname
    if final_host not in {"ilaios.com", "www.ilaios.com"}:
        raise RuntimeError(f"www alias resolved outside ILAIOS domains: {page.url}")
    return {"requested": WWW_URL, "status": response.status, "finalUrl": page.url, "xVercelId": response.headers.get("x-vercel-id")}


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    evidence: dict[str, Any] = {
        "status": "FAIL", "startedAt": started, "expectedSha": EXPECTED_SHA,
        "baseUrl": BASE_URL, "wwwUrl": WWW_URL, "release": None, "wwwAlias": None,
        "sitemapRouteCount": 0, "browserChecks": [], "error": None,
    }
    try:
        release = wait_for_exact_release(); evidence["release"] = release
        validate_robots(); urls = load_sitemap(); evidence["sitemapRouteCount"] = len(urls)
        checks: list[BrowserCheck] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=False, reduced_motion="reduce", locale="en-US")
            page = context.new_page(); evidence["wwwAlias"] = check_www_alias(page)
            for url in urls:
                for width, height in ALL_ROUTE_VIEWPORTS:
                    print(f"Checking {url} at {width}x{height}", flush=True)
                    checks.append(check_page(page, url, width, height))
            for path in sorted(CRITICAL_PATHS):
                url = f"{BASE_URL}{path}"
                for width, height in CRITICAL_EXTRA_VIEWPORTS:
                    print(f"Critical viewport {url} at {width}x{height}", flush=True)
                    checks.append(check_page(page, url, width, height))
            check_minimal_header(page, "/"); check_minimal_header(page, "/tr")
            for path, label in [("/", "home"), ("/tr", "home-tr"), ("/factories", "factories"), ("/contact", "contact"), ("/tr/contact", "contact-tr")]:
                for width, height in [(390, 844), (1440, 900)]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=30_000)
                    page.wait_for_timeout(250)
                    page.screenshot(path=str(ARTIFACT_DIR / f"{label}-{width}x{height}.png"), full_page=True)
            context.close(); browser.close()

        evidence["browserChecks"] = [asdict(check) for check in checks]
        evidence["status"] = "PASS"; evidence["completedAt"] = datetime.now(timezone.utc).isoformat()
        vercel_ids = sorted({check.x_vercel_id for check in checks if check.x_vercel_id})
        cancelled_prefetch_count = sum(len(check.cancelled_rsc_prefetches) for check in checks)
        summary = [
            "# ILAIOS Production Website Certification", "", "- Status: **PASS**",
            f"- Exact master SHA: `{EXPECTED_SHA}`", f"- Vercel deployment ID: `{release.get('deploymentId')}`",
            f"- Production environment: `{release.get('environment')}`", f"- Production URL: `{release.get('productionUrl')}`",
            f"- Sitemap routes: `{len(urls)}`", f"- Browser route/viewport checks: `{len(checks)}`",
            f"- Distinct x-vercel-id responses observed: `{len(vercel_ids)}`",
            f"- Browser-cancelled speculative Next.js RSC prefetches: `{cancelled_prefetch_count}` (recorded, non-blocking)",
            "- Minimal logo-only header: `PASS` for EN and TR",
            "- Horizontal overflow: `0 blocking findings`",
            "- Console/page/same-origin request failures: `0 blocking findings`",
        ]
        (ARTIFACT_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        evidence["error"] = str(exc); evidence["completedAt"] = datetime.now(timezone.utc).isoformat()
        (ARTIFACT_DIR / "summary.md").write_text(
            "# ILAIOS Production Website Certification\n\n"
            f"- Status: **FAIL**\n- Expected SHA: `{EXPECTED_SHA}`\n- Error: `{exc}`\n", encoding="utf-8",
        )
        print(f"CERTIFICATION FAILED: {exc}", file=sys.stderr, flush=True)
    finally:
        (ARTIFACT_DIR / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
