"""Fail-closed BrowserQA evidence validation for trusted Web agent certification.

This module does not execute or emulate BrowserQA. It accepts only the immutable
summary and boundary receipts produced by the current Docker-isolated real
Playwright CLI E2E. The caller must still bind the accepted evidence into the
canonical agent readiness/evidence chain; this validator cannot promote
readiness on its own.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class WebAgentBrowserCertificationError(RuntimeError):
    """BrowserQA evidence is missing, stale, malformed, or overclaims scope."""


_TARGET = "https://example.com/"
_REQUIRED_ACTIONS = ("snapshot", "screenshot", "reload", "close")


def verify_browser_egress_e2e_evidence(*, summary_path: Path, expected_source_sha: str) -> dict[str, object]:
    if len(expected_source_sha) != 40 or any(char not in "0123456789abcdef" for char in expected_source_sha):
        raise WebAgentBrowserCertificationError("expected source SHA must be exact lowercase git SHA")
    path = summary_path.resolve()
    if not path.is_file():
        raise WebAgentBrowserCertificationError("BrowserQA summary is unavailable")
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebAgentBrowserCertificationError("BrowserQA summary JSON is malformed") from exc
    if not isinstance(document, dict):
        raise WebAgentBrowserCertificationError("BrowserQA summary root must be an object")
    _validate_summary(document, expected_source_sha)
    receipt_names = document.get("egress_receipts")
    assert isinstance(receipt_names, list)
    receipt_root = (path.parent / "browser-egress-evidence").resolve()
    if not receipt_root.is_dir():
        raise WebAgentBrowserCertificationError("BrowserQA boundary receipt directory is unavailable")
    receipt_digests: list[str] = []
    for raw_name in receipt_names:
        if not isinstance(raw_name, str) or not raw_name.endswith(".json"):
            raise WebAgentBrowserCertificationError("BrowserQA receipt name is malformed")
        receipt_path = (receipt_root / raw_name).resolve()
        try:
            receipt_path.relative_to(receipt_root)
        except ValueError as exc:
            raise WebAgentBrowserCertificationError("BrowserQA receipt escapes evidence root") from exc
        if not receipt_path.is_file():
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt is missing")
        receipt_payload = receipt_path.read_bytes()
        if not receipt_payload:
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt is empty")
        try:
            receipt_document = json.loads(receipt_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt JSON is malformed") from exc
        if not isinstance(receipt_document, dict):
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt root must be an object")
        receipt_digests.append(hashlib.sha256(receipt_payload).hexdigest())
    if len(receipt_digests) < 6:
        raise WebAgentBrowserCertificationError("BrowserQA evidence contains insufficient egress receipts")
    combined_material = "\n".join(sorted(receipt_digests)).encode("ascii")
    return {
        "schema": "ilaios.web-agent.browser-tool-evidence.v1",
        "source_sha": expected_source_sha,
        "execution_mode": "browser-tool",
        "tool": "browser.playwright-cli",
        "browser_runtime_evidence": "PASS",
        "docker_egress_boundary_proven": True,
        "direct_public_ip_egress_blocked": True,
        "state_changing_browser_actions": False,
        "public_production_proven": False,
        "summary_sha256": hashlib.sha256(raw).hexdigest(),
        "egress_receipt_count": len(receipt_digests),
        "egress_receipts_sha256": hashlib.sha256(combined_material).hexdigest(),
    }


def _validate_summary(document: dict[str, Any], expected_source_sha: str) -> None:
    if document.get("schema_version") != 1:
        raise WebAgentBrowserCertificationError("unexpected BrowserQA summary schema")
    if document.get("source_sha") != expected_source_sha:
        raise WebAgentBrowserCertificationError("BrowserQA summary source SHA drifted")
    if document.get("target") != _TARGET:
        raise WebAgentBrowserCertificationError("BrowserQA certification target drifted")
    if document.get("allowed_origins") != [_TARGET.rstrip("/")]:
        raise WebAgentBrowserCertificationError("BrowserQA allowlist drifted")
    if document.get("javascript_enabled") is not False:
        raise WebAgentBrowserCertificationError("BrowserQA certification must keep JavaScript disabled")
    if document.get("service_workers") != "block":
        raise WebAgentBrowserCertificationError("BrowserQA certification must block service workers")
    if document.get("state_changing_browser_actions") is not False:
        raise WebAgentBrowserCertificationError("BrowserQA certification enabled state-changing actions")
    isolation = document.get("isolation_evidence_id")
    if not isinstance(isolation, str) or not isolation.startswith("sha256:"):
        raise WebAgentBrowserCertificationError("BrowserQA isolation evidence is missing")
    actions = document.get("actions")
    if not isinstance(actions, dict):
        raise WebAgentBrowserCertificationError("BrowserQA action evidence is missing")
    for action in _REQUIRED_ACTIONS:
        item = actions.get(action)
        if not isinstance(item, dict):
            raise WebAgentBrowserCertificationError(f"BrowserQA {action} evidence is missing")
        boundary = item.get("boundary_evidence_id")
        if not isinstance(boundary, str) or not boundary.startswith("sha256:"):
            raise WebAgentBrowserCertificationError(f"BrowserQA {action} lacks boundary evidence")
        if action != "close" and item.get("observed_url") != _TARGET:
            raise WebAgentBrowserCertificationError(f"BrowserQA {action} observed unexpected URL")
        if action in {"snapshot", "screenshot"}:
            digest = item.get("artifact_sha256")
            size = item.get("artifact_size")
            if not isinstance(digest, str) or len(digest) != 64:
                raise WebAgentBrowserCertificationError(f"BrowserQA {action} artifact digest is missing")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                raise WebAgentBrowserCertificationError(f"BrowserQA {action} artifact is empty")
    receipts = document.get("egress_receipts")
    if not isinstance(receipts, list) or len(receipts) < 6:
        raise WebAgentBrowserCertificationError("BrowserQA summary lacks egress receipt coverage")
