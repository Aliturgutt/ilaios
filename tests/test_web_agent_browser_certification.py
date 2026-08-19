from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.web_agent_browser_certification import (
    WebAgentBrowserCertificationError,
    verify_browser_egress_e2e_evidence,
)


def _write_receipts(root: Path, count: int = 6) -> list[str]:
    receipt_root = root / "browser-egress-evidence"
    receipt_root.mkdir(parents=True)
    names: list[str] = []
    for index in range(count):
        name = f"receipt-{index}.json"
        (receipt_root / name).write_text(json.dumps({"schema": "test", "index": index}), encoding="utf-8")
        names.append(name)
    return names


def _summary(source_sha: str, receipt_names: list[str]) -> dict[str, object]:
    boundary = "sha256:" + "1" * 64
    artifact = "2" * 64
    return {
        "schema_version": 1,
        "source_sha": source_sha,
        "runtime_image": f"ilaios-browser-e2e:{source_sha}",
        "target": "https://example.com/",
        "allowed_origins": ["https://example.com"],
        "javascript_enabled": False,
        "service_workers": "block",
        "state_changing_browser_actions": False,
        "seccomp_profile_git_blob_sha1": "fddc05fb520affb145404e6f6f647ca96af8087d",
        "isolation_evidence_id": boundary,
        "actions": {
            "open": {"returncode": 0, "boundary_evidence_id": boundary},
            "snapshot": {"boundary_evidence_id": boundary, "observed_url": "https://example.com/", "artifact_sha256": artifact, "artifact_size": 10},
            "screenshot": {"boundary_evidence_id": boundary, "observed_url": "https://example.com/", "artifact_sha256": artifact, "artifact_size": 20},
            "reload": {"boundary_evidence_id": boundary, "observed_url": "https://example.com/"},
            "close": {"boundary_evidence_id": boundary},
        },
        "egress_receipts": receipt_names,
    }


def test_accepts_exact_real_browser_egress_evidence(tmp_path: Path) -> None:
    source_sha = "a" * 40
    names = _write_receipts(tmp_path)
    summary_path = tmp_path / "playwright-cli-e2e-summary.json"
    summary_path.write_text(json.dumps(_summary(source_sha, names)), encoding="utf-8")
    result = verify_browser_egress_e2e_evidence(summary_path=summary_path, expected_source_sha=source_sha)
    assert result["browser_runtime_evidence"] == "PASS"
    assert result["execution_mode"] == "browser-tool"
    assert result["docker_egress_boundary_proven"] is True
    assert result["public_production_proven"] is False
    assert result["egress_receipt_count"] == 6


def test_rejects_stale_source_sha(tmp_path: Path) -> None:
    names = _write_receipts(tmp_path)
    summary_path = tmp_path / "playwright-cli-e2e-summary.json"
    summary_path.write_text(json.dumps(_summary("a" * 40, names)), encoding="utf-8")
    with pytest.raises(WebAgentBrowserCertificationError, match="source SHA drifted"):
        verify_browser_egress_e2e_evidence(summary_path=summary_path, expected_source_sha="b" * 40)


def test_rejects_state_changing_browser_actions(tmp_path: Path) -> None:
    source_sha = "a" * 40
    names = _write_receipts(tmp_path)
    document = _summary(source_sha, names)
    document["state_changing_browser_actions"] = True
    summary_path = tmp_path / "playwright-cli-e2e-summary.json"
    summary_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(WebAgentBrowserCertificationError, match="state-changing"):
        verify_browser_egress_e2e_evidence(summary_path=summary_path, expected_source_sha=source_sha)


def test_rejects_missing_boundary_receipt(tmp_path: Path) -> None:
    source_sha = "a" * 40
    names = _write_receipts(tmp_path)
    (tmp_path / "browser-egress-evidence" / names[-1]).unlink()
    summary_path = tmp_path / "playwright-cli-e2e-summary.json"
    summary_path.write_text(json.dumps(_summary(source_sha, names)), encoding="utf-8")
    with pytest.raises(WebAgentBrowserCertificationError, match="receipt is missing"):
        verify_browser_egress_e2e_evidence(summary_path=summary_path, expected_source_sha=source_sha)


def test_rejects_receipt_path_escape(tmp_path: Path) -> None:
    source_sha = "a" * 40
    names = _write_receipts(tmp_path)
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")
    names[-1] = "../outside.json"
    summary_path = tmp_path / "playwright-cli-e2e-summary.json"
    summary_path.write_text(json.dumps(_summary(source_sha, names)), encoding="utf-8")
    with pytest.raises(WebAgentBrowserCertificationError, match="receipt escapes evidence root"):
        verify_browser_egress_e2e_evidence(summary_path=summary_path, expected_source_sha=source_sha)
