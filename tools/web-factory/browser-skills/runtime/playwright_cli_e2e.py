from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import cast

from services.browser_runtime_composition import compose_browser_runtime
from services.control_plane.migrations import migrate_database
from services.governance.runtime import GovernedRuntimeGateway
from services.named_agent_executor import NamedAgentExecutor
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.browser_egress_playwright import PlaywrightDockerBrowserEgressBoundary
from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_AUTOMATION_SKILL_ID,
    BROWSER_CAPABILITY,
    BROWSER_TOOL_NAME,
    BrowserWorkReader,
    browser_session_id,
    submit_browser_request,
)
from src.core.audit_engine import AuditEngine
from src.core.bootstrap_validator import BootstrapValidator
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway

_TARGET = "https://example.com/"
_ALLOWED_ORIGINS = ("https://example.com",)
_SKILL_ID = "ilaios-web-e2e"
_REQUESTER_ID = "ci-browser"
_TENANT_ID = "ci-browser-tenant"
_REQUIRED_ACTIONS = ("open", "snapshot", "screenshot", "reload", "close")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value


def _git_value(repository_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    value = completed.stdout.strip()
    if not value:
        raise RuntimeError(f"git {' '.join(args)} returned no value")
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
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise RuntimeError(f"{action} artifact is empty")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_governed_interaction(
    *,
    governance: GovernedRuntimeGateway,
    tool_gateway: ToolGateway,
    audit: AuditEngine,
    session_id: str,
    source_sha: str,
) -> tuple[dict[str, object], dict[str, object]]:
    request_id = f"browser-press-{source_sha[:16]}"
    submit_browser_request(
        governance,
        request_id,
        _REQUESTER_ID,
        _TENANT_ID,
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
        raise RuntimeError(
            "high-risk browser interaction did not fail closed before approval"
        )

    governance.decide(request_id, "ci-independent-approver", "approved")
    after = governance.admission_snapshot(request_id)
    if after.get("risk") != "high":
        raise RuntimeError("approved browser interaction lost high-risk classification")
    if after.get("human_approval_required") is not True:
        raise RuntimeError("approved browser interaction lost HITL requirement")
    if after.get("approval_proven") is not True or after.get("admission_proven") is not True:
        raise RuntimeError(
            "approved browser interaction lacks durable approval/admission proof"
        )

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
    typed_result = cast(dict[str, object], result)
    _assert_observed(typed_result, "governed-press-tab")
    if typed_result.get("request_id") != request_id:
        raise RuntimeError("browser result is not bound to the governed request")

    latest = audit.get_latest()
    if latest is None or latest.component != "browser-tool":
        raise RuntimeError("governed browser interaction lacks audit evidence")
    if latest.action != "press" or latest.status != "success":
        raise RuntimeError(
            "governed browser interaction audit evidence is not successful"
        )

    state = governance.state()
    work = state.get("work")
    if not isinstance(work, list) or not any(
        isinstance(item, dict)
        and item.get("request_id") == request_id
        and item.get("status") == "executed"
        for item in work
    ):
        raise RuntimeError(
            "governed browser interaction did not reach durable executed state"
        )

    approval_evidence: dict[str, object] = {
        "before_approval": before,
        "after_approval": after,
        "audit_component": latest.component,
        "audit_action": latest.action,
        "audit_status": latest.status,
        "durable_work_status": "executed",
    }
    return typed_result, approval_evidence


def main() -> None:
    source_sha = _required_env("ILAIOS_SOURCE_SHA")
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise RuntimeError("ILAIOS_SOURCE_SHA must be an exact lowercase Git SHA")
    runtime_image = _required_env("ILAIOS_BROWSER_E2E_IMAGE")
    seccomp_profile = Path(_required_env("ILAIOS_BROWSER_SECCOMP_PROFILE")).resolve()
    artifact_root = Path(_required_env("ILAIOS_BROWSER_E2E_ARTIFACT_DIR")).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    repository_root = Path(__file__).resolve().parents[4]
    actual_head = _git_value(repository_root, "rev-parse", "HEAD")
    if actual_head != source_sha:
        raise RuntimeError("BrowserQA source SHA diverges from checked-out HEAD")
    branch = _git_value(repository_root, "branch", "--show-current")
    origin = _git_value(repository_root, "remote", "get-url", "origin")

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

    governance_database = artifact_root / "governed-browser-runtime.sqlite3"
    migrate_database(governance_database)
    runtime = GovernedRuntime(governance_database)
    grants = GrantPolicy()
    named = NamedAgentExecutor(runtime, grants)
    governance = GovernedRuntimeGateway(
        governance_database,
        runtime,
        hard_cap_minor=1000,
    )
    work_reader = BrowserWorkReader(governance, governance_database)
    audit = AuditEngine()
    context = ExecutionContext(repository_root, branch, source_sha, origin)
    tool_gateway = ToolGateway(context, BootstrapValidator(repository_root))
    compose_browser_runtime(
        named,
        repository_root,
        tool_gateway,
        governance,
        governance_database,
        frozenset(_ALLOWED_ORIGINS),
        boundary,
        audit,
        artifact_root,
        executable="playwright-cli",
        timeout_seconds=120,
    )

    workflow_id = source_sha
    session_id = browser_session_id(_REQUESTER_ID, _TENANT_ID, workflow_id)
    results: dict[str, dict[str, object]] = {}
    admission_evidence: list[dict[str, object]] = []
    persisted_work_evidence: list[dict[str, str]] = []

    def execute(
        index: int,
        action: str,
        *,
        operand: str | None = None,
        target_url: str | None = _TARGET,
    ) -> dict[str, object]:
        request_id = f"browser-e2e-{source_sha[:12]}-{index}-{action}"
        submitted = submit_browser_request(
            governance,
            request_id,
            _REQUESTER_ID,
            _TENANT_ID,
            workflow_id,
            _SKILL_ID,
            action,
            operand=operand,
            target_url=target_url,
        )
        if submitted.get("status") != "admitted":
            raise RuntimeError(f"{action} did not receive canonical browser admission")
        snapshot = governance.admission_snapshot(request_id)
        if snapshot.get("admission_proven") is not True:
            raise RuntimeError(f"{action} admission was not proven before tool dispatch")
        result = cast(
            dict[str, object],
            tool_gateway.dispatch(
                BROWSER_TOOL_NAME,
                request_id,
                session_id,
                action,
                operand,
                target_url,
            ),
        )
        if result.get("request_id") != request_id:
            raise RuntimeError(f"{action} tool result lost governed request identity")
        persisted = work_reader.read(request_id)
        if persisted.agent_id != BROWSER_AGENT_ID:
            raise RuntimeError("BrowserQA governed work lost canonical agent identity")
        if persisted.skill_id != _SKILL_ID:
            raise RuntimeError("BrowserQA governed work lost canonical skill identity")
        if persisted.capability != BROWSER_CAPABILITY:
            raise RuntimeError("BrowserQA governed work lost canonical capability identity")
        if persisted.status != "executed":
            raise RuntimeError("BrowserQA governed work did not reconcile to executed")
        persisted_work_evidence.append(
            {
                "request_id": request_id,
                "requester_id": persisted.requester_id,
                "agent_id": persisted.agent_id,
                "skill_id": persisted.skill_id,
                "capability": persisted.capability,
                "status": persisted.status,
                "action": action,
            }
        )
        admission_evidence.append(
            {
                "request_id": request_id,
                "action": action,
                "risk": snapshot.get("risk"),
                "admission_decision": snapshot.get("admission_decision"),
                "admission_proven": snapshot.get("admission_proven"),
                "reserved_minor": result.get("reserved_minor"),
            }
        )
        return result

    isolation_evidence: str | None = None
    approval_evidence: dict[str, object] | None = None
    automation_result: dict[str, object] | None = None
    try:
        results["open"] = execute(1, "open", operand=_TARGET)
        _assert_observed(results["open"], "open")
        isolation_evidence = boundary.verify_isolation(cwd=artifact_root)
        if not isolation_evidence.startswith("sha256:"):
            raise RuntimeError("Docker isolation probe lacks durable evidence")
        results["snapshot"] = execute(2, "snapshot")
        _assert_observed(results["snapshot"], "snapshot")
        _assert_artifact(results["snapshot"], "snapshot")
        results["screenshot"] = execute(3, "screenshot")
        _assert_observed(results["screenshot"], "screenshot")
        _assert_artifact(results["screenshot"], "screenshot")
        results["reload"] = execute(4, "reload")
        _assert_observed(results["reload"], "reload")

        automation_result, approval_evidence = _run_governed_interaction(
            governance=governance,
            tool_gateway=tool_gateway,
            audit=audit,
            session_id=session_id,
            source_sha=source_sha,
        )

        results["close"] = execute(5, "close", target_url=None)
    finally:
        boundary.shutdown()

    receipts = sorted(
        path.name for path in (artifact_root / "browser-egress-evidence").glob("*.json")
    )
    if len(receipts) < 7:
        raise RuntimeError("real BrowserQA E2E produced insufficient boundary receipts")

    if len(persisted_work_evidence) != 5:
        raise RuntimeError("BrowserQA persisted work identity coverage is incomplete")
    if {item["action"] for item in persisted_work_evidence} != set(_REQUIRED_ACTIONS):
        raise RuntimeError("BrowserQA persisted work action coverage drifted")
    if approval_evidence is None or automation_result is None:
        raise RuntimeError("governed browser interaction produced no approval evidence")

    audit_records = tuple(
        record
        for record in audit.get_records(component="browser-tool", status="success")
        if record.action in set(_REQUIRED_ACTIONS)
    )
    if len(audit_records) != 5:
        raise RuntimeError("BrowserQA audit evidence coverage is incomplete")
    if {record.action for record in audit_records} != set(_REQUIRED_ACTIONS):
        raise RuntimeError("BrowserQA audit action coverage drifted")

    admission_canonical = json.dumps(
        admission_evidence, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    work_canonical = json.dumps(
        persisted_work_evidence, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    summary = {
        "schema_version": 2,
        "source_sha": source_sha,
        "agent_id": BROWSER_AGENT_ID,
        "skill_id": _SKILL_ID,
        "capability": BROWSER_CAPABILITY,
        "runtime_image": runtime_image,
        "target": _TARGET,
        "allowed_origins": list(_ALLOWED_ORIGINS),
        "git_branch": branch,
        "git_origin": origin,
        "javascript_enabled": False,
        "service_workers": "block",
        "state_changing_browser_actions": False,
        "seccomp_profile_git_blob_sha1": "fddc05fb520affb145404e6f6f647ca96af8087d",
        "isolation_evidence_id": isolation_evidence,
        "direct_public_ip_egress_blocked": True,
        "canonical_tool_gateway": BROWSER_TOOL_NAME,
        "governed_work_persisted": True,
        "canonical_admission_proven": True,
        "governed_request_count": len(persisted_work_evidence),
        "audit_success_count": len(audit_records),
        "governance_database_sha256": _sha256_file(governance_database),
        "admission_evidence_sha256": hashlib.sha256(admission_canonical).hexdigest(),
        "governed_work_evidence_sha256": hashlib.sha256(work_canonical).hexdigest(),
        "admissions": admission_evidence,
        "governed_work": persisted_work_evidence,
        "actions": results,
        "egress_receipts": receipts,
        "governed_high_risk_interaction_verified": True,
        "interaction": "press Tab",
        "text_entry_actions_enabled": False,
        "production_interaction_requires_independent_approval": True,
        "approval_evidence": approval_evidence,
        "automation_action": automation_result,
    }
    summary_path = artifact_root / "playwright-cli-e2e-summary.json"
    summary_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "summary": str(summary_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
