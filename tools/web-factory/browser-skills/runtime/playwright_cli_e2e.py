from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from services.governance import GovernedRuntimeGateway
from services.runtime import GovernedRuntime
from services.runtime.browser_egress_docker import DockerBrowserEgressBoundary
from services.runtime.browser_egress_playwright import PlaywrightDockerBrowserEgressBoundary
from services.runtime.browser_tool_adapter import (
    BROWSER_AUTOMATION_SKILL_ID,
    BROWSER_TOOL_NAME,
    PlaywrightCliAdapter,
    browser_session_id,
    build_browser_tool_gateway,
    submit_browser_request,
)
from src.core.audit_engine import AuditEngine
from src.core.bootstrap_validator import BootstrapValidator
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway

_TARGET = "https://example.com/"
_ALLOWED_ORIGINS = ("https://example.com",)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value


def _run_git(repository_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _ensure_git_identity(repository_root: Path, source_sha: str) -> tuple[str, str]:
    if _run_git(repository_root, "rev-parse", "HEAD") != source_sha:
        raise RuntimeError("BrowserQA E2E checkout is not bound to exact source SHA")
    branch = _run_git(repository_root, "branch", "--show-current")
    if not branch:
        branch = f"ilaios-browser-e2e-{source_sha[:12]}"
        subprocess.run(
            ["git", "switch", "-c", branch],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    if _run_git(repository_root, "rev-parse", "HEAD") != source_sha:
        raise RuntimeError("BrowserQA E2E branch setup changed exact source SHA")
    origin = _run_git(repository_root, "remote", "get-url", "origin")
    if not origin:
        raise RuntimeError("BrowserQA E2E origin identity is unavailable")
    return branch, origin


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
    """Open the fixed public certification target with bounded diagnostics."""
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


def _run_governed_interaction(
    *,
    repository_root: Path,
    artifact_root: Path,
    boundary: PlaywrightDockerBrowserEgressBoundary,
    source_sha: str,
    branch: str,
    origin: str,
    session_id: str,
) -> tuple[dict[str, object], dict[str, object]]:
    governance_db = artifact_root / "governance.sqlite3"
    runtime_db = artifact_root / "runtime.sqlite3"
    governance = GovernedRuntimeGateway(
        governance_db,
        GovernedRuntime(runtime_db),
        hard_cap_minor=100,
    )
    audit = AuditEngine()
    context = ExecutionContext(repository_root, branch, source_sha, origin)
    tool_gateway = ToolGateway(context, BootstrapValidator(repository_root))
    build_browser_tool_gateway(
        tool_gateway,
        governance,
        governance_db,
        frozenset(_ALLOWED_ORIGINS),
        boundary,
        audit,
        artifact_root,
        executable="playwright-cli",
        timeout_seconds=120,
    )

    request_id = f"browser-press-{source_sha[:16]}"
    submit_browser_request(
        governance,
        request_id,
        "ci-browser",
        "ci-tenant",
        source_sha,
        BROWSER_AUTOMATION_SKILL_ID,
        "press",
        operand="Tab",
        target_url=_TARGET,
    )
    before = governance.admission_snapshot(request_id)
    if before != {
        "risk": "high",
        "admission_decision": "REQUIRE_APPROVAL",
        "human_approval_required": True,
        "approval_proven": False,
        "admission_proven": False,
    }:
        raise RuntimeError("high-risk browser interaction did not fail closed before approval")

    governance.decide(request_id, "ci-independent-approver", "approved")
    after = governance.admission_snapshot(request_id)
    if after.get("risk") != "high":
        raise RuntimeError("approved browser interaction lost high-risk classification")
    if after.get("human_approval_required") is not True:
        raise RuntimeError("approved browser interaction lost HITL requirement")
    if after.get("approval_proven") is not True or after.get("admission_proven") is not True:
        raise RuntimeError("approved browser interaction lacks durable approval/admission proof")

    result = tool_gateway.dispatch(
        BROWSER_TOOL_NAME,
        request_id,
        session_id,
        "press",
        "Tab",
        _TARGET,
    )
    if not isinstance(result, dict):
        raise RuntimeError("governed browser interaction returned an invalid result")
    _assert_observed(result, "governed-press-tab")
    if result.get("request_id") != request_id:
        raise RuntimeError("browser result is not bound to the governed request")

    latest = audit.get_latest()
    if latest is None or latest.component != "browser-tool":
        raise RuntimeError("governed browser interaction lacks audit evidence")
    if latest.action != "press" or latest.status != "success":
        raise RuntimeError("governed browser interaction audit evidence is not successful")

    state = governance.state()
    work = state.get("work")
    if not isinstance(work, list) or not any(
        isinstance(item, dict)
        and item.get("request_id") == request_id
        and item.get("status") == "executed"
        for item in work
    ):
        raise RuntimeError("governed browser interaction did not reach durable executed state")

    approval_evidence = {
        "before_approval": before,
        "after_approval": after,
        "audit_component": latest.component,
        "audit_action": latest.action,
        "audit_status": latest.status,
        "durable_work_status": "executed",
    }
    return result, approval_evidence


def main() -> None:
    source_sha = _required_env("ILAIOS_SOURCE_SHA")
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise RuntimeError("ILAIOS_SOURCE_SHA must be an exact lowercase Git SHA")
    runtime_image = _required_env("ILAIOS_BROWSER_E2E_IMAGE")
    seccomp_profile = Path(_required_env("ILAIOS_BROWSER_SECCOMP_PROFILE")).resolve()
    artifact_root = Path(
        _required_env("ILAIOS_BROWSER_E2E_ARTIFACT_DIR")
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    repository_root = Path(__file__).resolve().parents[4]
    branch, origin = _ensure_git_identity(repository_root, source_sha)
    proxy_script = (
        repository_root
        / "tools"
        / "web-factory"
        / "browser-skills"
        / "runtime"
        / "allowlist_proxy.py"
    )
    boundary = PlaywrightDockerBrowserEgressBoundary(
        runtime_image=runtime_image,
        proxy_script=proxy_script,
        seccomp_profile=seccomp_profile,
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
    approval_evidence: dict[str, object] | None = None
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

        governed_result, approval_evidence = _run_governed_interaction(
            repository_root=repository_root,
            artifact_root=artifact_root,
            boundary=boundary,
            source_sha=source_sha,
            branch=branch,
            origin=origin,
            session_id=session_id,
        )
        results["governed-press-tab"] = governed_result

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
    if len(receipts) < 7:
        raise RuntimeError("real BrowserQA E2E produced insufficient boundary receipts")
    if approval_evidence is None:
        raise RuntimeError("governed browser interaction produced no approval evidence")

    summary = {
        "schema_version": 3,
        "source_sha": source_sha,
        "runtime_image": runtime_image,
        "target": _TARGET,
        "allowed_origins": list(_ALLOWED_ORIGINS),
        "git_branch": branch,
        "git_origin": origin,
        "javascript_enabled": False,
        "service_workers": "block",
        "governed_high_risk_interaction_verified": True,
        "interaction": "press Tab",
        "text_entry_actions_enabled": False,
        "production_interaction_requires_independent_approval": True,
        "approval_evidence": approval_evidence,
        "seccomp_profile_git_blob_sha1": "fddc05fb520affb145404e6f6f647ca96af8087d",
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
