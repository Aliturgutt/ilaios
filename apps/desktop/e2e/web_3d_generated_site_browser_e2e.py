from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

from services.integrations.web_factory import GovernedWebFactory, derive_website_spec
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


_OBJECTIVE = (
    "Build a premium website with a 3D hero, scroll-driven camera motion, "
    "interactive product model rotation, parallax, particles, a WebGL background, "
    "3D typography, and touch interaction."
)
_EXPECTED_FEATURES = {
    "3d-hero",
    "scroll-camera",
    "product-rotation",
    "parallax",
    "particles",
    "webgl-background",
    "3d-typography",
    "pointer-interaction",
}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        del format, args


def main() -> int:
    repository = Path(__file__).resolve().parents[3]
    source_head = _git_head(repository)
    artifact_root_raw = os.environ.get("ILAIOS_WEB_3D_E2E_ARTIFACT_DIR", "").strip()
    if not artifact_root_raw:
        raise RuntimeError("ILAIOS_WEB_3D_E2E_ARTIFACT_DIR is required")
    artifact_root = Path(artifact_root_raw).resolve() / source_head
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    artifact_root.mkdir(parents=True)

    runtime_root = Path(tempfile.mkdtemp(prefix="ilaios-web3d-browser-e2e-"))
    server: ThreadingHTTPServer | None = None
    server_thread: threading.Thread | None = None
    try:
        now = datetime.now(timezone.utc)
        spec = derive_website_spec("web3d-generated-site-browser-e2e", _OBJECTIVE)
        if set(spec.features).intersection(_EXPECTED_FEATURES) != _EXPECTED_FEATURES:
            raise RuntimeError("explicit 3D objective did not resolve the complete capability set")
        acceptance = GovernedWebFactory(
            GrantPolicy(), runtime_root / "generated"
        ).build_generated_site(
            spec,
            grant=_grant(now, spec.site_id),
            now=now,
        )
        if not acceptance.accepted:
            raise RuntimeError("generated 3D site did not pass static acceptance")
        bundle = Path(acceptance.bundle_path).resolve()
        manifest_path = bundle / "acceptance.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        web3d = manifest.get("qa", {}).get("web3d", {})
        if web3d.get("status") != "SOURCE_INTEGRATED_NOT_BROWSER_CERTIFIED":
            raise RuntimeError("3D source integration evidence is missing before browser certification")
        if set(web3d.get("features", [])) != _EXPECTED_FEATURES:
            raise RuntimeError("3D acceptance manifest feature set differs from requested capability")

        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            lambda *args, **kwargs: _QuietHandler(
                *args, directory=str(bundle), **kwargs
            ),
        )
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=(
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                    "--use-angle=swiftshader",
                ),
            )
            normal = _normal_motion_proof(browser, base_url, artifact_root, web3d)
            reduced = _reduced_motion_proof(browser, base_url)
            mobile = _mobile_touch_proof(browser, base_url)
            browser.close()

        evidence = {
            "schema": "ilaios.web.3d-generated-site-browser-evidence.v1",
            "source_head_sha": source_head,
            "site_id": spec.site_id,
            "spec_hash": acceptance.spec_hash,
            "artifact_hash": acceptance.artifact_hash,
            "bundle_id": acceptance.bundle_id,
            "plan_sha256": web3d["plan_sha256"],
            "runtime_source_sha256": web3d["runtime_source_sha256"],
            "bundle_sha256": web3d["bundle_sha256"],
            "features": sorted(_EXPECTED_FEATURES),
            "normal_motion": normal,
            "reduced_motion": reduced,
            "mobile_touch": mobile,
            "browser_runtime_evidence": "PASS",
            "public_production_proven": False,
            "verification_scope": "LOCAL_GENERATED_SITE_CHROMIUM_3D_RUNTIME",
        }
        (artifact_root / "web3d-browser-evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(evidence, sort_keys=True))
        print("ILAIOS_WEB_3D_GENERATED_SITE_BROWSER_E2E=PASS")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None:
            server_thread.join(timeout=5)
        shutil.rmtree(runtime_root, ignore_errors=True)
    return 0


def _normal_motion_proof(
    browser: Browser,
    base_url: str,
    artifact_root: Path,
    web3d: dict[str, object],
) -> dict[str, object]:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        reduced_motion="no-preference",
    )
    try:
        page = context.new_page()
        response = page.goto(f"{base_url}/en/index.html", wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("generated 3D home route did not load in Chromium")
        _assert_parent_contract(page, web3d)
        frame = _runtime_frame(page)
        root = frame.locator("#ilaios-3d-root")
        root.wait_for(state="visible")
        if root.get_attribute("data-plan-sha") != web3d["plan_sha256"]:
            raise RuntimeError("browser runtime plan SHA differs from acceptance manifest")
        if root.get_attribute("data-fallback") == "on":
            raise RuntimeError("Chromium SwiftShader path unexpectedly fell back from WebGL")

        canvas = frame.locator("#scene")
        canvas.wait_for(state="visible")
        gl = canvas.evaluate(
            """canvas => {
                const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                if (!gl) return null;
                return {
                    version: String(gl.getParameter(gl.VERSION)),
                    width: gl.drawingBufferWidth,
                    height: gl.drawingBufferHeight
                };
            }"""
        )
        if not isinstance(gl, dict) or not gl.get("width") or not gl.get("height"):
            raise RuntimeError("WebGL drawing buffer was not established")

        before = artifact_root / "web3d-normal-before.png"
        after = artifact_root / "web3d-normal-after.png"
        canvas.screenshot(path=str(before))
        box = page.locator("iframe.ilaios-web3d-frame").bounding_box()
        if box is None:
            raise RuntimeError("3D iframe has no rendered bounding box")
        page.mouse.move(box["x"] + box["width"] * 0.8, box["y"] + box["height"] * 0.35)
        frame.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        time.sleep(0.25)
        canvas.screenshot(path=str(after))
        before_sha = _file_sha256(before)
        after_sha = _file_sha256(after)
        if before_sha == after_sha:
            raise RuntimeError("3D canvas did not produce observable motion/interaction change")
        return {
            "status": "PASS",
            "webgl": gl,
            "motion_frame_changed": True,
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "horizontal_overflow_px": _horizontal_overflow(page),
        }
    finally:
        context.close()


def _reduced_motion_proof(browser: Browser, base_url: str) -> dict[str, object]:
    context = browser.new_context(
        viewport={"width": 1024, "height": 768},
        reduced_motion="reduce",
    )
    try:
        page = context.new_page()
        response = page.goto(f"{base_url}/en/index.html", wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("reduced-motion generated 3D route did not load")
        frame = _runtime_frame(page)
        root = frame.locator("#ilaios-3d-root")
        root.wait_for(state="visible")
        if root.get_attribute("data-fallback") != "on":
            raise RuntimeError("prefers-reduced-motion did not force deterministic static fallback")
        fallback = frame.locator(".fallback")
        if not fallback.is_visible():
            raise RuntimeError("static reduced-motion alternative is not visible")
        if frame.locator("#scene").is_visible():
            raise RuntimeError("animated canvas remained visible under reduced motion")
        return {
            "status": "PASS",
            "mode": "static-2d-no-continuous-animation",
            "fallback_visible": True,
            "horizontal_overflow_px": _horizontal_overflow(page),
        }
    finally:
        context.close()


def _mobile_touch_proof(browser: Browser, base_url: str) -> dict[str, object]:
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        reduced_motion="no-preference",
    )
    try:
        page = context.new_page()
        response = page.goto(f"{base_url}/en/index.html", wait_until="networkidle")
        if response is None or response.status != 200:
            raise RuntimeError("mobile generated 3D route did not load")
        frame = _runtime_frame(page)
        root = frame.locator("#ilaios-3d-root")
        root.wait_for(state="visible")
        fallback = root.get_attribute("data-fallback") == "on"
        box = page.locator("iframe.ilaios-web3d-frame").bounding_box()
        if box is None:
            raise RuntimeError("mobile 3D iframe has no rendered bounding box")
        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + min(80, box["height"] / 2))
        overflow = _horizontal_overflow(page)
        if overflow > 1:
            raise RuntimeError(f"mobile 3D integration caused horizontal overflow: {overflow}")
        return {
            "status": "PASS",
            "touch_event_dispatched": True,
            "webgl_or_static_fallback": "static-2d" if fallback else "webgl",
            "horizontal_overflow_px": overflow,
        }
    finally:
        context.close()


def _assert_parent_contract(page: Page, web3d: dict[str, object]) -> None:
    container = page.locator("section.ilaios-web3d")
    iframe = container.locator("iframe.ilaios-web3d-frame")
    iframe.wait_for(state="visible")
    if iframe.get_attribute("sandbox") != "allow-scripts":
        raise RuntimeError("3D runtime iframe sandbox authority changed")
    if iframe.get_attribute("referrerpolicy") != "no-referrer":
        raise RuntimeError("3D runtime iframe referrer policy changed")
    if container.get_attribute("data-plan-sha") != web3d["plan_sha256"]:
        raise RuntimeError("parent page is not bound to the exact 3D plan SHA")
    csp = page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content") or ""
    if "script-src 'none'" not in csp:
        raise RuntimeError("parent generated page lost its script-deny CSP")
    overflow = _horizontal_overflow(page)
    if overflow > 1:
        raise RuntimeError(f"desktop 3D integration caused horizontal overflow: {overflow}")


def _runtime_frame(page: Page):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        for frame in page.frames:
            if frame.url.endswith("/assets/3d/index.html"):
                return frame
        time.sleep(0.05)
    raise RuntimeError("generated 3D iframe did not establish its browser frame")


def _horizontal_overflow(page: Page) -> float:
    return float(
        page.evaluate("Math.max(0, document.documentElement.scrollWidth - window.innerWidth)")
    )


def _grant(now: datetime, site_id: str) -> ExecutionGrant:
    return ExecutionGrant(
        "web3d-browser-e2e-grant",
        "web-worker",
        frozenset({"web.build"}),
        frozenset({site_id}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def _git_head(repository: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    head = completed.stdout.strip()
    if len(head) != 40:
        raise RuntimeError("exact source HEAD is invalid")
    return head


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
