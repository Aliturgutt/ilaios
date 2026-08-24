from __future__ import annotations

import pytest

from services.agent_final_closure import (
    AgentFinalClosureError,
    validate_agent_final_closure_receipt,
)
from services.agent_readiness import EXPECTED_AGENT_COUNT, EXPECTED_TEAM_COUNTS


def _receipt() -> dict[str, object]:
    return {
        "agent_workstream": "CLOSED",
        "exact_master_sha": "a" * 40,
        "canonical_agent_count": EXPECTED_AGENT_COUNT,
        "verified_agent_count": EXPECTED_AGENT_COUNT,
        "runtime_active_count": 3,
        "verified_family_breakdown": dict(EXPECTED_TEAM_COUNTS),
        "runtime_e2e_result": "VERIFIED",
        "provider_tool_execution_result": "VERIFIED",
        "g1_security_result": "VERIFIED",
        "evidence_integrity_result": "VERIFIED",
        "cost_usage_truth_result": "VERIFIED",
        "restart_recovery_result": "VERIFIED",
        "desktop_projection_result": "VERIFIED",
        "windows_msix_packaged_runtime_result": "VERIFIED",
        "cross_client_identity_tenant_result": "VERIFIED",
        "exact_head_release_governance_result": "VERIFIED",
        "exact_master_release_governance_result": "VERIFIED",
        "human_owner_required": True,
        "human_owner_state": "VERIFIED",
        "remaining_external_blockers": [],
        "closure_evidence_sha256": "b" * 64,
    }


def test_final_closure_receipt_accepts_complete_evidence_only() -> None:
    validate_agent_final_closure_receipt(_receipt())


def test_final_closure_receipt_rejects_incomplete_or_blocked_evidence() -> None:
    cases: list[tuple[str, object]] = [
        ("agent_workstream", "PARTIAL"),
        ("exact_master_sha", "unknown"),
        ("verified_agent_count", EXPECTED_AGENT_COUNT - 1),
        ("runtime_e2e_result", "NOT_VERIFIED"),
        ("provider_tool_execution_result", "PARTIAL"),
        ("evidence_integrity_result", "FAILED"),
        ("restart_recovery_result", "NOT_VERIFIED"),
        ("desktop_projection_result", "PARTIAL"),
        ("windows_msix_packaged_runtime_result", "BLOCKED_EXTERNAL"),
        ("cross_client_identity_tenant_result", "NOT_VERIFIED"),
        ("exact_head_release_governance_result", "PARTIAL"),
        ("exact_master_release_governance_result", "NOT_VERIFIED"),
        ("human_owner_state", "PARTIAL"),
        ("remaining_external_blockers", ["windows-user-machine"]),
    ]
    for field, value in cases:
        receipt = _receipt()
        receipt[field] = value
        with pytest.raises(AgentFinalClosureError):
            validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_rejects_registry_count_or_family_drift() -> None:
    receipt = _receipt()
    receipt["canonical_agent_count"] = EXPECTED_AGENT_COUNT + 1
    with pytest.raises(AgentFinalClosureError, match="canonical Agent count"):
        validate_agent_final_closure_receipt(receipt)

    receipt = _receipt()
    breakdown = dict(EXPECTED_TEAM_COUNTS)
    breakdown["web"] -= 1
    breakdown["media"] += 1
    receipt["verified_family_breakdown"] = breakdown
    with pytest.raises(AgentFinalClosureError, match="family breakdown"):
        validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_requires_human_owner_only_when_contract_requires_it() -> None:
    receipt = _receipt()
    receipt["human_owner_required"] = False
    receipt["human_owner_state"] = "NOT_REQUIRED"
    validate_agent_final_closure_receipt(receipt)
