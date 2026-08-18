from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from services.runtime.browser_egress_docker import DockerBrowserEgressBoundary
from services.runtime.browser_tool_adapter import PlaywrightCliAdapter, browser_session_id

_TARGET = "https://example.com/"
_ALLOWED_ORIGINS = ("https://example.com",)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value


def _assert_observed(result: dict[str, object], action: str) -> None:
    if result.get("observed_url") != _TARGET:
        raise RuntimeError(f"{action} did not observe the governed target URL")
    evidence_id = result.get("boundary_evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.startswith("sha256:"):
        raise RuntimeError(f"{action} lacks durable egress-boundary evidence")


def _assert_artifact(result: dict[str, object], action: str) -> None:
    digest = result.get("artifact_sha256")
    size = result.get("artifact_size")
    if not isinstance(digest, str) or len(digest) != 64:
        raise RuntimeError(f"{action} artifact digest is missing")
    if not isinstance(size, int) or size <= 0:
        raise RuntimeError(f"{action} artifact is empty")


def _diagnostic_open(
    boundary: DockerBrowserEgressBoundary,
    artifact_root: Path,
    session_id: str,
) -> dict[str, object]:
    """Open the fixed public certification target with bounded diagnostics.

    The production adapter intentionally does not surface raw browser stderr. This
    E2E-only path is safe to diagnose because target, argv and policy are fixed in
    source, no credentials are accepted, and the same Docker egress boundary is
    still mandatory.
    """
    process = boundary.run(
        allowed_origins=_ALLOWED_ORIGINS,
        argv=("playwright-cli", f"-s={session_id}", "open", _TARGET),
        cwd=artifact_root,
        timeout_seconds=120,
    )
    if process.returncode != 0:
        print("--- bounded playwright-cli stdout ---", file=sys.stderr)
        print(process.stdout[-4000:], file=sys.stderr)
        print("--- bounded playwright-cli stderr ---", file=sys.stderr)
        print(process.stderr[-4000:], file=sys.stderr)
        raise RuntimeError(
            f"bounded certification open failed with exit code {process.returncode}"
        )
    return {
        "returncode": process.returncode,
        "boundary_evidence_id": process.boundary_evidence_id,
    }


def main() -> None:
    source_sha = _required_env("ILAIOS_SOURCE_SHA")
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise RuntimeError("ILAIOS_SOURCE_SHA must be an exact lowercase Git SHA")
    runtime_image = _required_env("ILAIOS_BROWSER_E2E_IMAGE")
    artifact_root = Path(
        _required_env("ILAIOS_BROWSER_E2E_ARTIFACT_DIR")
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    repository_root = Path(__file__).resolve().parents[4]
    proxy_script = (
        repository_root
        / "tools"
        / "web-factory"
        / "browser-skills"
        / "runtime"
        / "allowlist_proxy.py"
    )
    boundary = DockerBrowserEgressBoundary(
        runtime_image=runtime_image,
        proxy_script=proxy_script,
    )
    cli = PlaywrightCliAdapter(
        boundary,
        artifact_root,
        executable="playwright-cli",
        timeout_seconds=120,
    )
    session_id = browser_session_id("ci-browser", "ci-tenant", source_sha)
    results: dict[str, dict[str, object]] = {}
    isolation_evidence: str | None = None
    try:
        results["open"] = _diagnostic_open(boundary, artifact_root, session_id)

        isolation_evidence = boundary.verify_isolation(cwd=artifact_root)
        if not isolation_evidence.startswith("sha256:"):
            raise RuntimeError("Docker isolation probe lacks durable evidence")

        results["snapshot"] = cli.execute(
            _ALLOWED_ORIGINS,
            session_id,
            "snapshot",
            None,
        )
        _assert_observed(results["snapshot"], "snapshot")
        _assert_artifact(results["snapshot"], "snapshot")

        results["screenshot"] = cli.execute(
            _ALLOWED_ORIGINS,
            session_id,
            "screenshot",
            None,
        )
        _assert_observed(results["screenshot"], "screenshot")
        _assert_artifact(results["screenshot"], "screenshot")

        results["reload"] = cli.execute(
            _ALLOWED_ORIGINS,
            session_id,
            "reload",
            None,
        )
        _assert_observed(results["reload"], "reload")

        results["close"] = cli.execute(
            _ALLOWED_ORIGINS,
            session_id,
            "close",
            None,
        )
    finally:
        boundary.shutdown()

    receipts = sorted(
        path.name
        for path in (artifact_root / "browser-egress-evidence").glob("*.json")
    )
    if len(receipts) < 6:
        raise RuntimeError("real BrowserQA E2E produced insufficient boundary receipts")

    summary = {
        "schema_version": 1,
        "source_sha": source_sha,
        "runtime_image": runtime_image,
        "target": _TARGET,
        "allowed_origins": list(_ALLOWED_ORIGINS),
        "javascript_enabled": False,
        "service_workers": "block",
        "state_changing_browser_actions": False,
        "isolation_evidence_id": isolation_evidence,
        "actions": results,
        "egress_receipts": receipts,
    }
    summary_path = artifact_root / "playwright-cli-e2e-summary.json"
    summary_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "summary": str(summary_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
