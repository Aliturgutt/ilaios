from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from playwright.sync_api import ConsoleMessage, sync_playwright

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
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 768, "height": 1024},
    {"width": 390, "height": 844},
)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        del format, args


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
        bundle_path = Path(str(manifest["bundle_path"])).resolve()
        if not bundle_path.is_dir():
            raise RuntimeError("accepted Web finished-product bundle is missing")
        source_project_path = Path(str(manifest["source_project_path"])).resolve()
        if not source_project_path.is_dir():
            raise RuntimeError("accepted Web source project is missing")

        site_output = artifact_root / "site"
        shutil.copytree(bundle_path, site_output)
        source_output = artifact_root / "source-project"
        shutil.copytree(source_project_path, source_output)
        _verify_tree_digest(site_output, str(manifest["artifact_digest"]))

        browser_receipt = _browser_certify(
            site_output,
            tuple(cast(list[str] | tuple[str, ...], manifest["routes"])),
            artifact_root,
        )
        evidence = {
            "schema": "ilaios.web.local-browser-evidence.v1",
            "source_head_sha": source_head,
            "request_id": manifest["request_id"],
            "adapter_id": manifest["adapter_id"],
            "source_commit_sha": manifest["source_commit_sha"],
            "source_commit_bound": manifest["source_commit_bound"],
            "artifact_digest": manifest["artifact_digest"],
            "source_project_digest": manifest["source_project_digest"],
            "routes": manifest["routes"],
            "local_acceptance": manifest["accepted"],
            "deployment_state": manifest["deployment_state"],
            "verification_scope": manifest["verification_scope"],
            "coordinator_status": coordinator_state["execution_status"],
            "coordinator_result_sha256": coordinator_state["result_sha256"],
            "browser_runtime_evidence": "PASS",
            "browser": browser_receipt,
        }
        (artifact_root / "browser-evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
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
    scheduler = DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=30),
    )
    grants = DurableGrantPolicy(database)
    evidence = EvidenceStore(root / "evidence")
    governance = GovernedRuntimeGateway(
        root / "governance.sqlite3",
        GovernedRuntime(database),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(
        root / "video",
        grants,
        governance,
        evidence,
    )
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
        "with clear navigation, accessible contact flow, responsive layout, and strong SEO essentials"
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
        raise RuntimeError("local Web E2E must not claim deployment")
    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("passed") is not True:
        raise RuntimeError("Web structural QA did not pass")

    coordinator_state = coordinator.get(
        request_id,
        principal_id="ci-web-user",
        tenant_id="ci-web-tenant",
    )
    if coordinator_state.get("execution_status") != "ACCEPTED":
        raise RuntimeError("canonical Coordinator did not accept Web finished product")
    return manifest, coordinator_state


def _browser_certify(
    site_root: Path,
    routes: tuple[str, ...],
    artifact_root: Path,
) -> dict[str, object]:
    handler = partial(_QuietHandler, directory=str(site_root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base_url = f"http://{host}:{port}"
    checks: list[dict[str, object]] = []
    try:
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
                        lambda message, errors=console_errors: _capture_console(
                            message, errors
                        ),
                    )
                    page.on(
                        "pageerror",
                        lambda error, errors=page_errors: errors.append(str(error)),
                    )
                    page.set_viewport_size(viewport)
                    response = page.goto(
                        f"{base_url}/{route}",
                        wait_until="networkidle",
                        timeout=30_000,
                    )
                    if response is None or response.status >= 400:
                        raise RuntimeError(
                            f"browser navigation failed for {route} at {viewport}"
                        )
                    if page.locator("main#main h1").count() != 1:
                        raise RuntimeError(f"main H1 missing for {route}")
                    if not page.locator("main#main h1").is_visible():
                        raise RuntimeError(f"main H1 is not visible for {route}")
                    if page.locator("nav a").count() < 4:
                        raise RuntimeError(f"navigation is incomplete for {route}")
                    if page.locator('link[rel="canonical"]').count() != 1:
                        raise RuntimeError(f"canonical SEO link missing for {route}")
                    if page.locator('meta[name="description"]').count() != 1:
                        raise RuntimeError(f"meta description missing for {route}")
                    if page.locator(".skip-link").count() != 1:
                        raise RuntimeError(f"skip link missing for {route}")
                    language = page.locator("html").get_attribute("lang")
                    expected_language = route.split("/", 1)[0]
                    if language != expected_language:
                        raise RuntimeError(
                            f"locale mismatch for {route}: {language} != {expected_language}"
                        )
                    overflow = page.evaluate(
                        "document.documentElement.scrollWidth - window.innerWidth"
                    )
                    if float(overflow) > 1:
                        raise RuntimeError(
                            f"horizontal overflow for {route} at {viewport}: {overflow}"
                        )
                    if route.endswith("contact.html"):
                        for selector in (
                            "#name",
                            "#email",
                            "#message",
                            'button[type="submit"]',
                        ):
                            if page.locator(selector).count() != 1:
                                raise RuntimeError(
                                    f"contact control {selector} missing for {route}"
                                )
                    if route.endswith("index.html") and len(
                        {r.split("/", 1)[0] for r in routes}
                    ) > 1:
                        if page.locator(".language-link").count() != 1:
                            raise RuntimeError(
                                f"language navigation missing for {route}"
                            )
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
                            "locale": language,
                            "horizontal_overflow_px": float(overflow),
                            "console_errors": 0,
                            "page_errors": 0,
                        }
                    )
                    if route.endswith("index.html") and viewport["width"] in {1440, 390}:
                        screenshot = artifact_root / (
                            f"{expected_language}-home-{viewport['width']}x{viewport['height']}.png"
                        )
                        page.screenshot(path=str(screenshot), full_page=True)
                    page.close()
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {
        "engine": "playwright-chromium",
        "viewports": list(VIEWPORTS),
        "route_count": len(routes),
        "checks": checks,
        "console_errors": 0,
        "page_errors": 0,
        "responsive": "PASS",
        "navigation": "PASS",
        "en_tr": "PASS",
        "accessibility_basics": "PASS",
        "seo_basics": "PASS",
        "runtime": "PASS",
    }


def _capture_console(message: ConsoleMessage, errors: list[str]) -> None:
    if message.type == "error":
        errors.append(message.text)


def _verify_tree_digest(site_root: Path, expected_digest: str) -> None:
    content: dict[str, bytes] = {}
    for path in site_root.rglob("*"):
        if path.is_file() and path.name != "acceptance.json":
            content[path.relative_to(site_root).as_posix()] = path.read_bytes()
    material = b"".join(
        path.encode() + b"\0" + body + b"\0"
        for path, body in sorted(content.items())
    )
    actual = hashlib.sha256(material).hexdigest()
    if actual != expected_digest:
        raise RuntimeError(
            f"persisted Web artifact digest mismatch: {actual} != {expected_digest}"
        )


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
