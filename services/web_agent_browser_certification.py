"""Fail-closed validation for trusted Web Agent BrowserQA evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_CAPABILITY,
    BROWSER_TOOL_NAME,
)
from services.web_agent_execution import web_binding_for


class WebAgentBrowserCertificationError(RuntimeError):
    """Governed BrowserQA evidence is missing, stale, malformed, or overclaims scope."""


_TARGET = "https://example.com/"
_REQUIRED_ACTIONS = ("open", "snapshot", "screenshot", "reload", "close")
_SKILL_ID = web_binding_for(BROWSER_AGENT_ID).primary_skill_id


def verify_browser_e2e_evidence(
    *, summary_path: Path, expected_source_sha: str
) -> dict[str, object]:
    if len(expected_source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in expected_source_sha
    ):
        raise WebAgentBrowserCertificationError(
            "expected source SHA must be exact lowercase git SHA"
        )
    path = summary_path.resolve()
    if not path.is_file():
        raise WebAgentBrowserCertificationError("BrowserQA summary is unavailable")
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebAgentBrowserCertificationError(
            "BrowserQA summary JSON is malformed"
        ) from exc
    if not isinstance(document, dict):
        raise WebAgentBrowserCertificationError("BrowserQA summary root must be an object")
    _validate_summary(document, expected_source_sha)

    receipt_names = document.get("egress_receipts")
    assert isinstance(receipt_names, list)
    receipt_root = (path.parent / "browser-egress-evidence").resolve()
    if not receipt_root.is_dir():
        raise WebAgentBrowserCertificationError("BrowserQA receipt directory is unavailable")
    receipt_digests: list[str] = []
    for raw_name in receipt_names:
        if not isinstance(raw_name, str) or not raw_name.endswith(".json"):
            raise WebAgentBrowserCertificationError("BrowserQA receipt name is malformed")
        receipt_path = (receipt_root / raw_name).resolve()
        try:
            receipt_path.relative_to(receipt_root)
        except ValueError as exc:
            raise WebAgentBrowserCertificationError(
                "BrowserQA receipt escapes evidence root"
            ) from exc
        if not receipt_path.is_file():
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt is missing")
        payload = receipt_path.read_bytes()
        if not payload:
            raise WebAgentBrowserCertificationError("BrowserQA boundary receipt is empty")
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebAgentBrowserCertificationError(
                "BrowserQA receipt JSON is malformed"
            ) from exc
        if not isinstance(parsed, dict):
            raise WebAgentBrowserCertificationError("BrowserQA receipt root must be an object")
        receipt_digests.append(hashlib.sha256(payload).hexdigest())
    if len(receipt_digests) < 6:
        raise WebAgentBrowserCertificationError(
            "BrowserQA egress receipt coverage is incomplete"
        )

    receipt_set = hashlib.sha256(
        "\n".join(sorted(receipt_digests)).encode("ascii")
    ).hexdigest()
    evidence = {
        "schema": "ilaios.web-agent.browser-tool-evidence.v2",
        "source_sha": expected_source_sha,
        "agent_id": BROWSER_AGENT_ID,
        "skill_id": _SKILL_ID,
        "capability": BROWSER_CAPABILITY,
        "execution_mode": "browser-tool",
        "tool": BROWSER_TOOL_NAME,
        "governed_work_persisted": True,
        "canonical_admission_proven": True,
        "docker_egress_boundary_proven": True,
        "direct_public_ip_egress_blocked": True,
        "state_changing_browser_actions": False,
        "public_production_proven": False,
        "summary_sha256": hashlib.sha256(raw).hexdigest(),
        "governance_database_sha256": document["governance_database_sha256"],
        "admission_evidence_sha256": document["admission_evidence_sha256"],
        "governed_work_evidence_sha256": document["governed_work_evidence_sha256"],
        "egress_receipt_count": len(receipt_digests),
        "egress_receipts_sha256": receipt_set,
    }
    canonical = json.dumps(
        evidence, sort_keys=True, separators=(",", ":")
    ).encode()
    evidence["evidence_digest"] = hashlib.sha256(canonical).hexdigest()
    return evidence


def _require_sha256(document: dict[str, Any], key: str) -> None:
    value = document.get(key)
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise WebAgentBrowserCertificationError(f"BrowserQA {key} is not SHA-256")


def _validate_summary(document: dict[str, Any], expected_source_sha: str) -> None:
    if document.get("schema_version") != 2:
        raise WebAgentBrowserCertificationError("unexpected BrowserQA summary schema")
    required_exact = {
        "source_sha": expected_source_sha,
        "agent_id": BROWSER_AGENT_ID,
        "skill_id": _SKILL_ID,
        "capability": BROWSER_CAPABILITY,
        "target": _TARGET,
        "allowed_origins": [_TARGET.rstrip("/")],
        "javascript_enabled": False,
        "service_workers": "block",
        "state_changing_browser_actions": False,
        "direct_public_ip_egress_blocked": True,
        "canonical_tool_gateway": BROWSER_TOOL_NAME,
        "governed_work_persisted": True,
        "canonical_admission_proven": True,
        "governed_request_count": 5,
        "audit_success_count": 5,
    }
    for key, expected in required_exact.items():
        if document.get(key) != expected:
            raise WebAgentBrowserCertificationError(f"BrowserQA {key} drifted")
    isolation = document.get("isolation_evidence_id")
    if not isinstance(isolation, str) or not isolation.startswith("sha256:"):
        raise WebAgentBrowserCertificationError("BrowserQA isolation evidence is missing")
    _require_sha256(document, "governance_database_sha256")
    _require_sha256(document, "admission_evidence_sha256")
    _require_sha256(document, "governed_work_evidence_sha256")

    admissions = document.get("admissions")
    if not isinstance(admissions, list) or len(admissions) != 5:
        raise WebAgentBrowserCertificationError(
            "BrowserQA admission evidence coverage is incomplete"
        )
    admission_actions: set[str] = set()
    for item in admissions:
        if not isinstance(item, dict):
            raise WebAgentBrowserCertificationError("BrowserQA admission entry is malformed")
        action = item.get("action")
        if not isinstance(action, str):
            raise WebAgentBrowserCertificationError("BrowserQA admission action is missing")
        admission_actions.add(action)
        if (
            item.get("admission_proven") is not True
            or item.get("admission_decision") != "ALLOW"
        ):
            raise WebAgentBrowserCertificationError("BrowserQA admission was not proven")
    if admission_actions != set(_REQUIRED_ACTIONS):
        raise WebAgentBrowserCertificationError(
            "BrowserQA admission action coverage drifted"
        )

    governed_work = document.get("governed_work")
    if not isinstance(governed_work, list) or len(governed_work) != 5:
        raise WebAgentBrowserCertificationError(
            "BrowserQA persisted work evidence coverage is incomplete"
        )
    work_actions: set[str] = set()
    for item in governed_work:
        if not isinstance(item, dict):
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work entry is malformed"
            )
        action = item.get("action")
        if not isinstance(action, str):
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work action is missing"
            )
        work_actions.add(action)
        if item.get("agent_id") != BROWSER_AGENT_ID:
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work agent identity drifted"
            )
        if item.get("skill_id") != _SKILL_ID:
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work skill identity drifted"
            )
        if item.get("capability") != BROWSER_CAPABILITY:
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work capability drifted"
            )
        if item.get("status") != "executed":
            raise WebAgentBrowserCertificationError(
                "BrowserQA persisted work is not executed"
            )
    if work_actions != set(_REQUIRED_ACTIONS):
        raise WebAgentBrowserCertificationError(
            "BrowserQA persisted work action coverage drifted"
        )

    actions = document.get("actions")
    if not isinstance(actions, dict) or set(actions) != set(_REQUIRED_ACTIONS):
        raise WebAgentBrowserCertificationError(
            "BrowserQA action evidence coverage drifted"
        )
    for action in _REQUIRED_ACTIONS:
        item = actions.get(action)
        if not isinstance(item, dict):
            raise WebAgentBrowserCertificationError(
                f"BrowserQA {action} evidence is missing"
            )
        boundary = item.get("boundary_evidence_id")
        if not isinstance(boundary, str) or not boundary.startswith("sha256:"):
            raise WebAgentBrowserCertificationError(
                f"BrowserQA {action} boundary evidence is missing"
            )
        if action != "close" and item.get("observed_url") != _TARGET:
            raise WebAgentBrowserCertificationError(f"BrowserQA {action} URL drifted")
        if action in {"snapshot", "screenshot"}:
            digest = item.get("artifact_sha256")
            size = item.get("artifact_size")
            if not isinstance(digest, str) or len(digest) != 64:
                raise WebAgentBrowserCertificationError(
                    f"BrowserQA {action} digest is missing"
                )
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                raise WebAgentBrowserCertificationError(
                    f"BrowserQA {action} artifact is empty"
                )

    receipts = document.get("egress_receipts")
    if not isinstance(receipts, list) or len(receipts) < 6:
        raise WebAgentBrowserCertificationError("BrowserQA receipt list is incomplete")
