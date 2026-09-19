from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_CAPABILITY,
    BROWSER_TOOL_NAME,
)
from services.web_agent_browser_certification import (
    WebAgentBrowserCertificationError,
    verify_browser_e2e_evidence,
)
from services.web_agent_execution import web_binding_for

_SOURCE_SHA = "a" * 40
_SKILL_ID = web_binding_for(BROWSER_AGENT_ID).primary_skill_id
_REQUIRED_ACTIONS = ("open", "snapshot", "screenshot", "reload", "close")


def _write_receipts(root: Path, count: int = 6) -> list[str]:
    receipt_root = root / "browser-egress-evidence"
    receipt_root.mkdir(parents=True)
    result: list[str] = []
    for index in range(count):
        name = f"receipt-{index}.json"
        (receipt_root / name).write_text(
            json.dumps({"index": index}, sort_keys=True), encoding="utf-8"
        )
        result.append(name)
    return result


def _document(receipts: list[str]) -> dict[str, object]:
    boundary = "sha256:" + "b" * 64
    artifact = "c" * 64
    actions = {
        "open": {"boundary_evidence_id": boundary, "observed_url": "https://example.com/"},
        "snapshot": {
            "boundary_evidence_id": boundary,
            "observed_url": "https://example.com/",
            "artifact_sha256": artifact,
            "artifact_size": 10,
        },
        "screenshot": {
            "boundary_evidence_id": boundary,
            "observed_url": "https://example.com/",
            "artifact_sha256": artifact,
            "artifact_size": 20,
        },
        "reload": {"boundary_evidence_id": boundary, "observed_url": "https://example.com/"},
        "close": {"boundary_evidence_id": boundary},
    }
    admissions = [
        {
            "request_id": f"request-{index}",
            "action": action,
            "risk": "medium" if action in {"open", "reload"} else "low",
            "admission_decision": "ALLOW",
            "admission_proven": True,
            "reserved_minor": 10,
        }
        for index, action in enumerate(_REQUIRED_ACTIONS, 1)
    ]
    governed_work = [
        {
            "request_id": f"request-{index}",
            "requester_id": "ci-browser",
            "agent_id": BROWSER_AGENT_ID,
            "skill_id": _SKILL_ID,
            "capability": BROWSER_CAPABILITY,
            "status": "executed",
            "action": action,
        }
        for index, action in enumerate(_REQUIRED_ACTIONS, 1)
    ]
    return {
        "schema_version": 2,
        "source_sha": _SOURCE_SHA,
        "agent_id": BROWSER_AGENT_ID,
        "skill_id": _SKILL_ID,
        "capability": BROWSER_CAPABILITY,
        "runtime_image": f"ilaios-browser-e2e:{_SOURCE_SHA}",
        "target": "https://example.com/",
        "allowed_origins": ["https://example.com"],
        "javascript_enabled": False,
        "service_workers": "block",
        "state_changing_browser_actions": False,
        "seccomp_profile_git_blob_sha1": "fddc05fb520affb145404e6f6f647ca96af8087d",
        "isolation_evidence_id": boundary,
        "direct_public_ip_egress_blocked": True,
        "canonical_tool_gateway": BROWSER_TOOL_NAME,
        "governed_work_persisted": True,
        "canonical_admission_proven": True,
        "governed_request_count": 5,
        "audit_success_count": 5,
        "governance_database_sha256": "d" * 64,
        "admission_evidence_sha256": "e" * 64,
        "governed_work_evidence_sha256": "f" * 64,
        "admissions": admissions,
        "governed_work": governed_work,
        "actions": actions,
        "egress_receipts": receipts,
    }


def _write_summary(root: Path, document: dict[str, object]) -> Path:
    path = root / "playwright-cli-e2e-summary.json"
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return path


def test_accepts_exact_governed_browser_evidence(tmp_path: Path) -> None:
    receipts = _write_receipts(tmp_path)
    path = _write_summary(tmp_path, _document(receipts))
    evidence = verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)
    assert evidence["agent_id"] == BROWSER_AGENT_ID
    assert evidence["skill_id"] == _SKILL_ID
    assert evidence["capability"] == BROWSER_CAPABILITY
    assert evidence["execution_mode"] == "browser-tool"
    assert evidence["canonical_admission_proven"] is True
    assert evidence["governed_work_persisted"] is True
    assert evidence["public_production_proven"] is False
    assert len(str(evidence["evidence_digest"])) == 64


def test_rejects_stale_source_sha(tmp_path: Path) -> None:
    path = _write_summary(tmp_path, _document(_write_receipts(tmp_path)))
    with pytest.raises(WebAgentBrowserCertificationError, match="source_sha drifted"):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha="0" * 40)


def test_rejects_missing_governed_admission(tmp_path: Path) -> None:
    document = _document(_write_receipts(tmp_path))
    document["canonical_admission_proven"] = False
    path = _write_summary(tmp_path, document)
    with pytest.raises(
        WebAgentBrowserCertificationError, match="canonical_admission_proven drifted"
    ):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)


def test_rejects_wrong_agent_or_skill(tmp_path: Path) -> None:
    document = _document(_write_receipts(tmp_path))
    document["agent_id"] = "ilaios.agent.web.ux.v1"
    path = _write_summary(tmp_path, document)
    with pytest.raises(WebAgentBrowserCertificationError, match="agent_id drifted"):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)


def test_rejects_persisted_work_identity_drift(tmp_path: Path) -> None:
    document = _document(_write_receipts(tmp_path))
    work = document["governed_work"]
    assert isinstance(work, list)
    assert isinstance(work[0], dict)
    work[0]["agent_id"] = "ilaios.agent.web.ux.v1"
    path = _write_summary(tmp_path, document)
    with pytest.raises(
        WebAgentBrowserCertificationError, match="persisted work agent identity drifted"
    ):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)


def test_rejects_state_changing_actions(tmp_path: Path) -> None:
    document = _document(_write_receipts(tmp_path))
    document["state_changing_browser_actions"] = True
    path = _write_summary(tmp_path, document)
    with pytest.raises(
        WebAgentBrowserCertificationError, match="state_changing_browser_actions drifted"
    ):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)


def test_rejects_receipt_path_escape(tmp_path: Path) -> None:
    receipts = _write_receipts(tmp_path)
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")
    receipts[-1] = "../outside.json"
    path = _write_summary(tmp_path, _document(receipts))
    with pytest.raises(
        WebAgentBrowserCertificationError, match="receipt escapes evidence root"
    ):
        verify_browser_e2e_evidence(summary_path=path, expected_source_sha=_SOURCE_SHA)
