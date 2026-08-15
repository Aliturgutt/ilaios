#!/usr/bin/env python3
"""Collect real browser evidence for a generated Web Factory artifact."""

from __future__ import annotations

import importlib
import json
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

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


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        del format, args


def _measure(page: Any) -> dict[str, object]:
    value = page.evaluate(
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
              const rect = el.getBoundingClientRect();
              return rect.left < -1 || rect.right > window.innerWidth + 1;
            })
            .map((el) => ({
              tag: el.tagName,
              cls: el.className,
              rect: el.getBoundingClientRect().toJSON(),
            }));
          const controls = [...document.querySelectorAll('.primary-action,button,input,textarea')]
            .filter(visible)
            .map((el) => {
              const rect = el.getBoundingClientRect();
              return {tag: el.tagName, width: rect.width, height: rect.height};
            });
          const main = document.querySelector('main');
          const canonical = document.querySelector('link[rel="canonical"]');
          return {
            viewport: window.innerWidth,
            documentOverflow: Math.max(
              0,
              document.documentElement.scrollWidth - document.documentElement.clientWidth,
            ),
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
    )
    if not isinstance(value, dict):
        raise RuntimeError("browser measurement payload is malformed")
    return cast(dict[str, object], value)


def _append_browser_findings(
    findings: list[dict[str, object]],
    *,
    route: str,
    locale: str,
    width: int,
    measured: dict[str, object],
    console_errors: list[str],
    page_errors: list[str],
    request_failures: list[str],
) -> None:
    def add(finding: str) -> None:
        findings.append({"route": route, "width": width, "finding": finding})

    if measured.get("lang") != locale:
        add("locale mismatch")
    if measured.get("mainVisible") is not True:
        add("main not visible")
    if not measured.get("canonical"):
        add("canonical missing")
    if measured.get("documentOverflow") != 0 or measured.get("bodyOverflow") != 0:
        add("horizontal overflow")
    overflow = measured.get("overflowElements")
    if isinstance(overflow, list) and overflow:
        add("element exceeds viewport")
    if console_errors or page_errors or request_failures:
        add("browser runtime error")

    controls = measured.get("controls")
    if isinstance(controls, list):
        for control_value in controls:
            if not isinstance(control_value, dict):
                add("malformed control measurement")
                break
            width_value = control_value.get("width")
            height_value = control_value.get("height")
            if not isinstance(width_value, (int, float)) or not isinstance(
                height_value, (int, float)
            ):
                add("malformed control measurement")
                break
            if width_value < 32 or height_value < 32:
                add("undersized primary control")
                break


def main() -> int:
    root = Path("artifacts/web-factory-browser-evidence")
    root.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 8, 16, tzinfo=timezone.utc)
    objective = (
        "Create a premium bilingual Turkish/English website for a professional "
        "law firm focused on corporate clients, with contact conversion, strong "
        "trust presentation and responsive mobile design."
    )

    sync_api = importlib.import_module("playwright.sync_api")
    findings: list[dict[str, object]] = []
    measurements: list[dict[str, object]] = []

    with TemporaryDirectory() as temporary:
        temp = Path(temporary)
        spec = derive_website_spec("web-browser-certification", objective)
        result = GovernedWebFactory(GrantPolicy(), temp / "artifacts").build_generated_site(
            spec,
            grant=_grant(spec.site_id, now),
            now=now,
        )
        bundle = Path(result.bundle_path)
        handler = partial(_QuietHandler, directory=str(bundle))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = int(server.server_address[1])
        try:
            with sync_api.sync_playwright() as playwright:
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

                            def on_console(message: Any) -> None:
                                if message.type == "error":
                                    console_errors.append(str(message.text))

                            def on_page_error(error: Any) -> None:
                                page_errors.append(str(error))

                            def on_request_failed(request: Any) -> None:
                                request_failures.append(str(request.url))

                            page.on("console", on_console)
                            page.on("pageerror", on_page_error)
                            page.on("requestfailed", on_request_failed)
                            response = page.goto(
                                f"http://127.0.0.1:{port}/{route}",
                                wait_until="networkidle",
                            )
                            if response is None or response.status != 200:
                                findings.append(
                                    {
                                        "route": route,
                                        "width": width,
                                        "finding": "non-200 route",
                                    }
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
                            measurements.append(measured)
                            _append_browser_findings(
                                findings,
                                route=route,
                                locale=locale,
                                width=width,
                                measured=measured,
                                console_errors=console_errors,
                                page_errors=page_errors,
                                request_failures=request_failures,
                            )

                            page.keyboard.press("Tab")
                            focused = page.evaluate(
                                "document.activeElement !== document.body && "
                                "document.activeElement !== document.documentElement"
                            )
                            if focused is not True:
                                findings.append(
                                    {
                                        "route": route,
                                        "width": width,
                                        "finding": "keyboard focus missing",
                                    }
                                )
                            reduced = page.evaluate(
                                "matchMedia('(prefers-reduced-motion: reduce)').matches && "
                                "getComputedStyle(document.documentElement).scrollBehavior === 'auto'"
                            )
                            if reduced is not True:
                                findings.append(
                                    {
                                        "route": route,
                                        "width": width,
                                        "finding": "reduced motion not honored",
                                    }
                                )
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

    summary: dict[str, object] = {
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
    public_summary = {key: value for key, value in summary.items() if key != "measurements"}
    print(json.dumps(public_summary, sort_keys=True))
    if findings:
        raise SystemExit("Web Factory browser evidence failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
