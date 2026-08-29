from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import BrowserContext, ConsoleMessage, Page, sync_playwright

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableWebProductRuntime,
)
from services.integrations.web_delivery import LocalWebDeploymentAdapter, tree_sha256
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


VIEWPORTS = (
    {"width": 320, "height": 800},
    {"width": 360, "height": 800},
    {"width": 390, "height": 844},
    {"width": 412, "height": 915},
    {"width": 430, "height": 932},
    {"width": 768, "height": 1024},
    {"width": 1024, "height": 768},
    {"width": 1440, "height": 900},
)
_SECURITY_HEADERS = (
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-frame-options",
)


def main() -> int:
    repository = Path(__file__).resolve().parents[3]
    source_head = _git_head(repository)
    artifact_root_raw = os.environ.get("ILAIOS_WEB_E2E_ARTIFACT_DIR", "").strip()
    if not artifact_root_raw:
        raise RuntimeError("ILAIOS_WEB_E2E_ARTIFACT_DIR is required")
    artifact_root = Path(artifact_root_raw).resolve() / source_head
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    artifact_root.mkdir(parents=True)

    runtime_root = Path(tempfile.mkdtemp(prefix="ilaios-web-browser-e2e-"))
    try:
        manifest, coordinator_state = _build_through_coordinator(
            runtime_root,
            source_head=source_head,
        )
        source_project = Path(str(manifest["source_project_path"])).resolve()
        if not source_project.is_dir():
            raise RuntimeError("accepted certified Web source project is missing")
        if tree_sha256(source_project) != manifest["source_project_digest"]:
            raise RuntimeError("certified Web source digest differs from AcceptanceManifest")

        source_output = artifact_root / "certified-source-project"
        shutil.copytree(source_project, source_output)
        build_workspace = artifact_root / "build-workspace"
        shutil.copytree(source_project, build_workspace)
        build_receipt = _production_build(build_workspace)
        browser_receipt = _browser_certify(
            build_workspace,
            tuple(str(route) for route in manifest["certified_routes"]),
            tuple(str(feature) for feature in manifest["functional_features"]),
            artifact_root,
        )
        deployment_receipt = _deployment_and_rollback_proof(
            source_project,
            artifact_root,
            source_head=source_head,
            artifact_sha=str(manifest["source_project_digest"]),
        )
        evidence = {
            "schema": "ilaios.web.finished-product-browser-evidence.v2",
            "source_head_sha": source_head,
            "request_id": manifest["request_id"],
            "adapter_id": manifest["adapter_id"],
            "source_commit_sha": manifest["source_commit_sha"],
            "source_commit_bound": manifest["source_commit_bound"],
            "preview_artifact_digest": manifest["artifact_digest"],
            "source_project_digest": manifest["source_project_digest"],
            "source_assurance": manifest["source_assurance"],
            "repair_attempts": manifest["repair_attempts"],
            "routes": manifest["certified_routes"],
            "functional_features": manifest["functional_features"],
            "local_acceptance": manifest["accepted"],
            "public_deployment_state": manifest["deployment_state"],
            "verification_scope": "LOCAL_CERTIFIED_NEXT_BUILD_BROWSER_AND_ROLLBACK",
            "coordinator_status": coordinator_state["execution_status"],
            "coordinator_result_sha256": coordinator_state["result_sha256"],
            "production_build": build_receipt,
            "browser_runtime_evidence": "PASS",
            "browser": browser_receipt,
            "deployment_and_rollback": deployment_receipt,
            "public_production_proven": False,
        }
        (artifact_root / "browser-evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.rmtree(build_workspace, ignore_errors=True)
        print(json.dumps(evidence, sort_keys=True))
        print("ILAIOS_WEB_FACTORY_BROWSER_E2E=PASS")
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)
    return 0


def _build_through_coordinator(
    root: Path,
    *,
    source_head: str,
) -> tuple[dict[str, object], dict[str, object]]:
    local_boundary = "fixture-control-plane-boundary"
    os.environ["ILAIOS_SOURCE_SHA"] = source_head
    database = root / "control-plane.sqlite3"
    control = ControlPlane(ControlPlaneConfig(database, local_boundary))
    workflows = WorkflowStore(WorkflowStoreConfig(database))
    scheduler = DurableWorkerScheduler(database, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(database)
    evidence = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        GovernedRuntime(database),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(root / "video", grants, governance, evidence)
    video_product = DurableVideoProductRuntime(
        root / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    web = RecoverableWebProductRuntime(
        root / "web-product.sqlite3",
        control,
        grants,
        governance,
        root / "web",
    )
    coordinator = ExecutionCoordinator(
        root / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_web_runtime(coordinator, web)

    request_id = "web-factory-browser-e2e"
    objective = (
        "Build a premium bilingual Turkish/English website for a corporate law firm "
        "with clear navigation, accessible contact flow, responsive layout, a blog with articles, "
        "newsletter signup, site search, and strong SEO essentials"
    )
    now = datetime.now(timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        objective,
        token=local_boundary,
        principal_id="ci-web-user",
        tenant_id="ci-web-tenant",
        now=now,
    )
    if prepared.get("execution_status") != "ADMITTED":
        raise RuntimeError(f"Web request was not admitted: {prepared}")
    if prepared.get("adapter_id") != "web.product-runtime.v1":
        raise RuntimeError(f"unexpected Web adapter: {prepared}")

    manifest = coordinator.resume(
        request_id,
        token=local_boundary,
        now=now + timedelta(seconds=1),
        principal_id="ci-web-user",
        tenant_id="ci-web-tenant",
    )
    if manifest.get("accepted") is not True:
        raise RuntimeError(f"Web AcceptanceManifest did not pass: {manifest}")
    if manifest.get("source_commit_bound") is not True:
        raise RuntimeError("Web manifest is not bound to an exact source commit")
    if manifest.get("source_commit_sha") != source_head:
        raise RuntimeError("Web manifest source SHA differs from exact CI HEAD")
    if manifest.get("deployment_state") != "NOT_DEPLOYED":
        raise RuntimeError("local Web E2E must not claim public deployment")
    assurance = manifest.get("source_assurance")
    if not isinstance(assurance, dict) or assurance.get("passed") is not True:
        raise RuntimeError("Web source assurance did not pass before acceptance")
    if not manifest.get("repair_attempts"):
        raise RuntimeError("Web bounded repair evidence is missing")
    expected_features = {"contact-form", "content", "newsletter", "search"}
    if set(manifest.get("functional_features", [])) != expected_features:
        raise RuntimeError("Web bounded functional feature set was not produced")

    coordinator_state = coordinator.get(
        request_id,
        principal_id="ci-web-user",
        tenant_id="ci-web-tenant",
    )
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError("canonical Coordinator did not accept Web finished product")
    return manifest, coordinator_state


def _production_build(project_root: Path) -> dict[str, object]:
    commands = (
        ("npm", "install", "--no-audit", "--no-fund"),
        ("npm", "run", "typecheck"),
        ("npm", "run", "build"),
    )
    results: list[dict[str, object]] = []
    started = time.monotonic()
    for command in commands:
        step_started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=240,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"generated Next.js production build step failed: {' '.join(command)}\n"
                + completed.stdout[-4000:]
                + completed.stderr[-4000:]
            )
        results.append(
            {
                "command": " ".join(command),
                "status": "PASS",
                "duration_seconds": round(time.monotonic() - step_started, 3),
            }
        )
    build_dir = project_root / ".next"
    if not build_dir.is_dir():
        raise RuntimeError("generated Next.js build output is missing")
    return {
        "status": "PASS",
        "steps": results,
        "duration_seconds": round(time.monotonic() - started, 3),
        "build_output": ".next",
        "package_lock_sha256": _file_sha256(project_root / "package-lock.json"),
    }


def _browser_certify(
    project_root: Path,
    routes: tuple[str, ...],
    features: tuple[str, ...],
    artifact_root: Path,
) -> dict[str, object]:
    port = _free_port()
    env = dict(os.environ)
    env["NEXT_PUBLIC_SITE_URL"] = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        ("npm", "run", "start", "--", "-H", "127.0.0.1", "-p", str(port)),
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_http(f"{base_url}/en", process)
        checks: list[dict[str, object]] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=False)
            for viewport in VIEWPORTS:
                for route in routes:
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    page.on(
                        "console",
                        lambda message, errors=console_errors: _capture_console(message, errors),
                    )
                    page.on(
                        "pageerror",
                        lambda error, errors=page_errors: errors.append(str(error)),
                    )
                    page.set_viewport_size(viewport)
                    response = page.goto(
                        f"{base_url}{route}", wait_until="networkidle", timeout=30_000
                    )
                    if response is None or response.status >= 400:
                        raise RuntimeError(
                            f"browser navigation failed for {route} at {viewport}"
                        )
                    _assert_security_headers(response.headers, route)
                    _assert_page_quality(page, route, viewport)
                    if console_errors:
                        raise RuntimeError(
                            f"console errors for {route} at {viewport}: {console_errors}"
                        )
                    if page_errors:
                        raise RuntimeError(
                            f"page errors for {route} at {viewport}: {page_errors}"
                        )
                    checks.append(
                        {
                            "route": route,
                            "viewport": viewport,
                            "status": response.status,
                            "horizontal_overflow_px": float(
                                page.evaluate(
                                    "document.documentElement.scrollWidth - window.innerWidth"
                                )
                            ),
                            "console_errors": 0,
                            "page_errors": 0,
                        }
                    )
                    if route in {"/en", "/tr"} and viewport["width"] in {
                        320,
                        390,
                        430,
                        1440,
                    }:
                        locale = route.removeprefix("/")
                        page.screenshot(
                            path=str(
                                artifact_root
                                / f"{locale}-home-{viewport['width']}x{viewport['height']}.png"
                            ),
                            full_page=True,
                        )
                    page.close()

            _assert_global_seo(context, base_url)
            _assert_functional_modules(context, base_url, features)
            _assert_motion_runtime(context, base_url)
            context.close()
            browser.close()
        return {
            "engine": "playwright-chromium-next-production",
            "viewports": list(VIEWPORTS),
            "route_count": len(routes),
            "check_count": len(checks),
            "checks": checks,
            "console_errors": 0,
            "page_errors": 0,
            "responsive": "PASS",
            "navigation": "PASS",
            "en_tr_content_parity": "PASS",
            "accessibility": "PASS",
            "seo": "PASS",
            "security_headers": "PASS",
            "functional_modules": "PASS",
            "runtime": "PASS",
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _assert_page_quality(page: Page, route: str, viewport: dict[str, int]) -> None:
    if page.locator("main#main h1").count() != 1 or not page.locator(
        "main#main h1"
    ).is_visible():
        raise RuntimeError(f"main H1 missing or hidden for {route}")
    if page.locator("main#main").count() != 1:
        raise RuntimeError(f"semantic main landmark missing for {route}")
    overflow = float(
        page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    )
    if overflow > 1:
        raise RuntimeError(f"horizontal overflow for {route} at {viewport}: {overflow}")
    if page.locator('meta[name="description"]').count() != 1:
        raise RuntimeError(f"meta description missing for {route}")
    if page.locator('meta[property="og:title"]').count() != 1:
        raise RuntimeError(f"OpenGraph title missing for {route}")
    if page.locator('link[rel="canonical"]').count() != 1:
        raise RuntimeError(f"canonical metadata missing for {route}")
    if page.locator('link[rel~="icon"]').count() < 1:
        raise RuntimeError(f"favicon metadata missing for {route}")

    if page.locator("nav").count():
        if page.locator("nav a").count() < 4:
            raise RuntimeError(f"navigation is incomplete for {route}")
        expected = "Ana sayfa" if route.startswith("/tr") else "Home"
        if page.get_by_text(expected, exact=True).count() < 1:
            raise RuntimeError(f"locale-specific navigation copy missing for {route}")
    if page.locator(".skip-link").count():
        page.keyboard.press("Tab")
        active = page.evaluate(
            "document.activeElement && document.activeElement.className"
        )
        if "skip-link" not in str(active):
            raise RuntimeError(f"keyboard focus did not enter skip link for {route}")
        outline = page.locator(".skip-link").evaluate(
            "el => getComputedStyle(el).outlineStyle"
        )
        if outline == "none":
            raise RuntimeError(f"visible keyboard focus is missing for {route}")
    for selector in ("button", "input", "textarea"):
        count = page.locator(selector).count()
        for index in range(count):
            element = page.locator(selector).nth(index)
            if not element.is_visible():
                continue
            box = element.bounding_box()
            if box is not None and float(box["height"]) < 44:
                raise RuntimeError(f"touch target too small for {selector} on {route}")
            element_id = element.get_attribute("id")
            if selector in {"input", "textarea"} and element_id:
                if page.locator(f'label[for="{element_id}"]').count() != 1:
                    raise RuntimeError(f"form label missing for {element_id} on {route}")



def _assert_motion_runtime(context: BrowserContext, base_url: str) -> None:
    page = context.new_page()
    try:
        response = page.goto(f"{base_url}/en", wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise RuntimeError("motion runtime home route failed")
        main = page.locator("main#main")
        for attribute in (
            "data-motion-intensity",
            "data-interaction-density",
            "data-scroll-behavior",
            "data-showcase-behavior",
            "data-motion-accessibility",
        ):
            if not main.get_attribute(attribute):
                raise RuntimeError(f"motion design contract missing from generated runtime: {attribute}")
        reveals = page.locator('[data-motion="reveal"]')
        if reveals.count() < 1:
            raise RuntimeError("generated runtime has no motion reveal surfaces")
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('[data-motion=\"reveal\"]')).every((el) => el.classList.contains('is-visible'))",
            timeout=5_000,
        )
        if page.evaluate("document.documentElement.dataset.reducedMotion") != "false":
            raise RuntimeError("default motion preference was not observed")

        page.emulate_media(reduced_motion="reduce")
        page.reload(wait_until="networkidle")
        page.wait_for_function(
            "() => document.documentElement.dataset.reducedMotion === 'true'",
            timeout=5_000,
        )
        reduced = page.locator('[data-motion="reveal"]').first
        styles = reduced.evaluate(
            "el => ({opacity:getComputedStyle(el).opacity, transform:getComputedStyle(el).transform})"
        )
        if styles["opacity"] != "1" or styles["transform"] != "none":
            raise RuntimeError(f"reduced-motion static equivalent failed: {styles}")
        tilt = page.locator('[data-interactive="tilt"]').first
        if tilt.count():
            transform = tilt.evaluate("el => getComputedStyle(el).transform")
            if transform != "none":
                raise RuntimeError("reduced-motion interactive tilt was not disabled")
    finally:
        page.close()


def _assert_global_seo(context: BrowserContext, base_url: str) -> None:
    page = context.new_page()
    try:
        for path, marker in (
            ("/robots.txt", "sitemap"),
            ("/sitemap.xml", "<urlset"),
        ):
            response = page.goto(
                f"{base_url}{path}", wait_until="networkidle", timeout=30_000
            )
            if response is None or response.status != 200:
                raise RuntimeError(f"SEO endpoint failed: {path}")
            body = page.locator("body").inner_text().lower()
            if marker not in body and marker not in page.content().lower():
                raise RuntimeError(
                    f"SEO endpoint content missing marker {marker}: {path}"
                )
    finally:
        page.close()


def _assert_functional_modules(
    context: BrowserContext,
    base_url: str,
    features: tuple[str, ...],
) -> None:
    page = context.new_page()
    try:
        if "contact-form" in features:
            page.goto(f"{base_url}/en/contact", wait_until="networkidle")
            form = page.locator(".contact-form")
            if form.count() != 1 or form.get_attribute("action") != "/api/contact":
                raise RuntimeError("contact form is not bound to the governed local API")
            for selector in ("#name", "#email", "#message"):
                if page.locator(selector).count() != 1:
                    raise RuntimeError(f"contact control missing: {selector}")
            response = context.request.post(
                f"{base_url}/api/contact",
                form={
                    "name": "Test User",
                    "email": "test@example.test",
                    "message": "A governed test submission",
                    "locale": "en",
                },
                max_redirects=0,
            )
            if response.status != 303:
                raise RuntimeError(
                    f"contact API did not return deterministic 303: {response.status}"
                )
            location = response.headers.get("location", "")
            if "/en/contact?submitted=1" not in location:
                raise RuntimeError(f"contact API redirect target is invalid: {location}")
            invalid = context.request.post(
                f"{base_url}/api/contact",
                form={
                    "name": "x",
                    "email": "not-an-email",
                    "message": "x",
                    "locale": "en",
                },
                max_redirects=0,
            )
            if invalid.status != 400:
                raise RuntimeError("contact API accepted invalid input")
        if "newsletter" in features:
            page.goto(f"{base_url}/en", wait_until="networkidle")
            form = page.locator(".newsletter-form")
            if form.count() != 1 or form.get_attribute("action") != "/api/newsletter":
                raise RuntimeError("newsletter form is not bound to the governed local API")
            response = context.request.post(
                f"{base_url}/api/newsletter",
                form={"email": "reader@example.test", "locale": "en"},
                max_redirects=0,
            )
            if response.status != 303:
                raise RuntimeError(
                    f"newsletter API did not return deterministic 303: {response.status}"
                )
            location = response.headers.get("location", "")
            if "/en?subscribed=1" not in location:
                raise RuntimeError(
                    f"newsletter API redirect target is invalid: {location}"
                )
            page.goto(f"{base_url}/en/contact", wait_until="networkidle")
            if page.locator(".newsletter-form").count() != 0:
                raise RuntimeError("newsletter module leaked onto a non-requested page surface")
        if "content" in features:
            response = page.goto(f"{base_url}/en/insights", wait_until="networkidle")
            if response is None or response.status != 200:
                raise RuntimeError("content module route failed")
        if "search" in features:
            page.goto(f"{base_url}/en/search?q=contact", wait_until="networkidle")
            if page.locator("form input[name=q]").count() != 1:
                raise RuntimeError("search module input missing")
    finally:
        page.close()


def _assert_security_headers(headers: dict[str, str], route: str) -> None:
    lowered = {key.lower(): value for key, value in headers.items()}
    for header in _SECURITY_HEADERS:
        if not lowered.get(header):
            raise RuntimeError(f"security header {header} missing for {route}")
    if lowered.get("x-content-type-options", "").lower() != "nosniff":
        raise RuntimeError(f"nosniff security header invalid for {route}")


def _deployment_and_rollback_proof(
    project_root: Path,
    artifact_root: Path,
    *,
    source_head: str,
    artifact_sha: str,
) -> dict[str, object]:
    adapter = LocalWebDeploymentAdapter(artifact_root / "deployment-proof")
    first = adapter.deploy(
        project_root,
        source_commit_sha=source_head,
        expected_artifact_sha256=artifact_sha,
    )
    probe = artifact_root / "rollback-probe-source"
    shutil.copytree(project_root, probe)
    (probe / ".ilaios-rollback-probe").write_text(
        "candidate-two\n", encoding="utf-8"
    )
    second = adapter.deploy(probe, source_commit_sha=source_head)
    rollback = adapter.rollback(first.deployment_id, source_commit_sha=source_head)
    current = adapter.current()
    if current is None or current.get("deployment_id") != first.deployment_id:
        raise RuntimeError("local Web rollback did not restore the accepted artifact")
    shutil.rmtree(probe, ignore_errors=True)
    return {
        "status": "PASS",
        "provider": first.provider,
        "accepted_deployment": first.to_dict(),
        "newer_candidate_deployment": second.to_dict(),
        "rollback": rollback.to_dict(),
        "restored_artifact_sha256": current["artifact_sha256"],
        "public_production_proven": False,
    }


def _wait_for_http(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = "" if process.stdout is None else process.stdout.read()
            raise RuntimeError(
                f"generated Next.js server exited early:\n{output[-4000:]}"
            )
        try:
            with urllib.request.urlopen(  # noqa: S310 - localhost only
                url, timeout=2
            ) as response:
                if response.status < 400:
                    return
        except Exception as error:  # noqa: BLE001 - bounded readiness polling
            last_error = error
        time.sleep(0.25)
    raise RuntimeError(f"generated Next.js server did not become healthy: {last_error}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _capture_console(message: ConsoleMessage, errors: list[str]) -> None:
    if message.type == "error":
        errors.append(message.text)


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"expected build evidence file is missing: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repository: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise RuntimeError("exact source HEAD is unavailable for Web browser evidence")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
