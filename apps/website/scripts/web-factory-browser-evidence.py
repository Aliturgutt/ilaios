#!/usr/bin/env python3
"""Collect real browser evidence for a generated Web Factory artifact."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from playwright.sync_api import ConsoleMessage, Error, Page, Request, sync_playwright

from services.integrations import GovernedWebFactory, derive_website_spec
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy

VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)


def _grant(site_id: str, now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "web-browser-evidence-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({site_id}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def _quiet_handler(directory: str) -> type[SimpleHTTPRequestHandler]:
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return cast(
        type[SimpleHTTPRequestHandler],
        partial(QuietHandler, directory=directory),
    )


def _measure(page: Page) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        page.evaluate(
            """
            () => {
              const visible = (el) => {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                  Number(style.opacity || 1) !== 0 && rect.width > 0 && rect.height > 0;
              };
              const overflow = [...document.querySelectorAll('*')]
                .filter((el) => visible(el) && !el.classList.contains('skip-link'))
                .filter((el) => {
                  const r = el.getBoundingClientRect();
                  return r.left < -1 || r.right > window.innerWidth + 1;
                })
                .map((el) => ({tag: el.tagName, cls: el.className, rect: el.getBoundingClientRect().toJSON()}));
              const controls = [...document.querySelectorAll('.primary-action,button,input,textarea')]
                .filter(visible)
                .map((el) => {
                  const r = el.getBoundingClientRect();
                  return {tag: el.tagName, width: r.width, height: r.height};
                });
              const main = document.querySelector('main');
              const canonical = document.querySelector('link[rel="canonical"]');
              return {
                viewport: window.innerWidth,
                documentOverflow: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
                bodyOverflow: Math.max(0, document.body.scrollWidth - document.body.clientWidth),
                overflowElements: overflow,
                controls,
                lang: document.documentElement.lang,
                mainVisible: !!main && visible(main),
                canonical: canonical ? canonical.href : null,
                title: document.title,
              };
            }
            """
        ),
    )


def main() -> int:
    root = Path("artifacts/web-factory-browser-evidence")
    root.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 8, 16, tzinfo=timezone.utc)
    objective = (
        "Create a premium bilingual Turkish/English website for a professional "
        "law firm focused on corporate clients, with contact conversion, strong "
        "trust presentation and responsive mobile design."
    )

    with TemporaryDirectory() as temporary:
        temp = Path(temporary)
        spec = derive_website_spec("web-browser-certification", objective)
        result = GovernedWebFactory(GrantPolicy(), temp / "artifacts").build_generated_site(
            spec,
            grant=_grant(spec.site_id, now),
            now=now,
        )
        bundle = Path(result.bundle_path)
        handler = _quiet_handler(str(bundle))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = int(server.server_address[1])
        findings: list[dict[str, object]] = []
        measurements: list[dict[str, object]] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    for route in result.routes:
                        locale = route.split("/", 1)[0]
                        for width in VIEWPORTS:
                            page = browser.new_page(
                                viewport={"width": width, "height": 900},
                                reduced_motion="reduce",
                            )
                            console_errors: list[str] = []
                            page_errors: list[str] = []
                            request_failures: list[str] = []

                            def on_console(message: ConsoleMessage) -> None:
                                if message.type == "error":
                                    console_errors.append(message.text)

                            def on_page_error(error: Error) -> None:
                                page_errors.append(str(error))

                            def on_request_failed(request: Request) -> None:
                                request_failures.append(request.url)

                            page.on("console", on_console)
                            page.on("pageerror", on_page_error)
                            page.on("requestfailed", on_request_failed)
                            response = page.goto(
                                f"http://127.0.0.1:{port}/{route}",
                                wait_until="networkidle",
                            )
                            if response is None or response.status != 200:
                                findings.append(
                                    {"route": route, "width": width, "finding": "non-200 route"}
                                )
                                page.close()
                                continue
                            measured = _measure(page)
                            measured.update(
                                {
                                    "route": route,
                                    "consoleErrors": console_errors,
                                    "pageErrors": page_errors,
                                    "requestFailures": request_failures,
                                }
                            )
                            measurements.append(cast(dict[str, object], measured))
                            if measured["lang"] != locale:
                                findings.append({"route": route, "width": width, "finding": "locale mismatch"})
                            if not measured["mainVisible"]:
                                findings.append({"route": route, "width": width, "finding": "main not visible"})
                            if not measured["canonical"]:
                                findings.append({"route": route, "width": width, "finding": "canonical missing"})
                            if measured["documentOverflow"] != 0 or measured["bodyOverflow"] != 0:
                                findings.append({"route": route, "width": width, "finding": "horizontal overflow"})
                            if measured["overflowElements"]:
                                findings.append({"route": route, "width": width, "finding": "element exceeds viewport"})
                            if console_errors or page_errors or request_failures:
                                findings.append({"route": route, "width": width, "finding": "browser runtime error"})
                            for control in cast(list[dict[str, float]], measured["controls"]):
                                if control["height"] < 32 or control["width"] < 32:
                                    findings.append({"route": route, "width": width, "finding": "undersized primary control"})
                                    break
                            page.keyboard.press("Tab")
                            focused = page.evaluate(
                                "document.activeElement !== document.body && document.activeElement !== document.documentElement"
                            )
                            if not focused:
                                findings.append({"route": route, "width": width, "finding": "keyboard focus missing"})
                            reduced = page.evaluate(
                                "matchMedia('(prefers-reduced-motion: reduce)').matches && getComputedStyle(document.documentElement).scrollBehavior === 'auto'"
                            )
                            if not reduced:
                                findings.append({"route": route, "width": width, "finding": "reduced motion not honored"})
                            if route.endswith("index.html"):
                                page.screenshot(
                                    path=str(root / f"{locale}-{width}.png"),
                                    full_page=True,
                                )
                            page.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    summary = {
        "status": "PASS" if not findings else "FAIL",
        "artifact_digest": result.artifact_hash,
        "routes": result.routes,
        "viewports": VIEWPORTS,
        "measurement_count": len(measurements),
        "findings": findings,
        "measurements": measurements,
    }
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "measurements"}, sort_keys=True))
    if findings:
        raise SystemExit("Web Factory browser evidence failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
