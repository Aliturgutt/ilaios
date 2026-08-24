from __future__ import annotations

import pytest

from services.agent_final_closure import (
    AgentFinalClosureError,
    validate_agent_final_closure_receipt,
)
from services.agent_readiness import EXPECTED_AGENT_COUNT, EXPECTED_TEAM_COUNTS
from services.agent_registry import CANONICAL_AGENT_REGISTRY


def _canonical_agent_ids() -> list[str]:
    return [item.manifest.agent_id for item in CANONICAL_AGENT_REGISTRY]


def _agent_evidence_refs() -> list[str]:
    return [
        f"evidence://exec-final-001/{agent_id}" for agent_id in _canonical_agent_ids()
    ]


def _agent_evidence_bindings() -> dict[str, str]:
    return {
        agent_id: f"evidence://exec-final-001/{agent_id}"
        for agent_id in _canonical_agent_ids()
    }


def _receipt() -> dict[str, object]:
    return {
        "agent_workstream": "CLOSED",
        "exact_master_sha": "a" * 40,
        "canonical_agent_count": EXPECTED_AGENT_COUNT,
        "verified_agent_count": EXPECTED_AGENT_COUNT,
        "verified_agent_ids": _canonical_agent_ids(),
        "runtime_active_count": 3,
        "verified_family_breakdown": dict(EXPECTED_TEAM_COUNTS),
        "registry_identity_result": "VERIFIED",
        "runtime_state_truth_result": "VERIFIED",
        "runtime_e2e_result": "VERIFIED",
        "family_runtime_execution_result": "VERIFIED",
        "provider_tool_execution_result": "VERIFIED",
        "provider_tool_receipt_binding_result": "VERIFIED",
        "browser_tool_egress_security_result": "VERIFIED",
        "g1_security_result": "VERIFIED",
        "evidence_integrity_result": "VERIFIED",
        "execution_evidence_lineage_result": "VERIFIED",
        "cross_tenant_artifact_evidence_substitution_result": "VERIFIED",
        "cost_usage_truth_result": "VERIFIED",
        "tenant_bound_cost_usage_result": "VERIFIED",
        "restart_recovery_result": "VERIFIED",
        "operations_meta_runtime_result": "VERIFIED",
        "desktop_projection_result": "VERIFIED",
        "windows_msix_packaged_runtime_result": "VERIFIED",
        "cross_client_identity_tenant_result": "VERIFIED",
        "exact_head_release_governance_result": "VERIFIED",
        "exact_master_release_governance_result": "VERIFIED",
        "execution_id": "exec-final-001",
        "job_id": "job-final-001",
        "user_id": "user-final-001",
        "tenant_id": "tenant-final-001",
        "session_id": "session-final-001",
        "skill_route": "ilaios.skill.final-certification.v1",
        "tool_route": "ilaios.tool.gateway/governed",
        "provider_route": "openrouter/zero-cost-governed",
        "runtime_e2e_evidence_ref": "evidence://exec-final-001/runtime-e2e",
        "g1_security_evidence_ref": "evidence://exec-final-001/g1-security",
        "evidence_integrity_evidence_ref": "evidence://exec-final-001/integrity",
        "restart_recovery_evidence_ref": "evidence://exec-final-001/restart-recovery",
        "desktop_projection_evidence_ref": "evidence://exec-final-001/desktop-projection",
        "windows_msix_evidence_ref": "evidence://exec-final-001/windows-msix",
        "exact_head_ci_evidence_ref": "github-actions://required-ci/head",
        "exact_master_ci_evidence_ref": "github-actions://required-ci/master",
        "agent_execution_evidence_refs": _agent_evidence_refs(),
        "agent_execution_evidence_bindings": _agent_evidence_bindings(),
        "provider_tool_receipt_ids": ["receipt-provider-001", "receipt-tool-001"],
        "output_artifact_sha256": "c" * 64,
        "output_validation_result": "VERIFIED",
        "cost_usage_evidence_ref": "evidence://exec-final-001/cost-usage",
        "human_owner_evidence_ref": "evidence://exec-final-001/human-owner",
        "evidence_record_id": "evidence-final-001",
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
        ("verified_agent_ids", []),
        ("registry_identity_result", "NOT_VERIFIED"),
        ("runtime_state_truth_result", "PARTIAL"),
        ("runtime_e2e_result", "NOT_VERIFIED"),
        ("family_runtime_execution_result", "NOT_VERIFIED"),
        ("provider_tool_execution_result", "PARTIAL"),
        ("provider_tool_receipt_binding_result", "NOT_VERIFIED"),
        ("browser_tool_egress_security_result", "FAILED"),
        ("g1_security_result", "FAILED"),
        ("evidence_integrity_result", "FAILED"),
        ("execution_evidence_lineage_result", "PARTIAL"),
        ("cross_tenant_artifact_evidence_substitution_result", "FAILED"),
        ("cost_usage_truth_result", "NOT_VERIFIED"),
        ("tenant_bound_cost_usage_result", "NOT_VERIFIED"),
        ("restart_recovery_result", "NOT_VERIFIED"),
        ("operations_meta_runtime_result", "PARTIAL"),
        ("desktop_projection_result", "PARTIAL"),
        ("windows_msix_packaged_runtime_result", "BLOCKED_EXTERNAL"),
        ("cross_client_identity_tenant_result", "NOT_VERIFIED"),
        ("exact_head_release_governance_result", "PARTIAL"),
        ("exact_master_release_governance_result", "NOT_VERIFIED"),
        ("execution_id", ""),
        ("job_id", ""),
        ("tenant_id", ""),
        ("provider_route", ""),
        ("runtime_e2e_evidence_ref", ""),
        ("g1_security_evidence_ref", ""),
        ("evidence_integrity_evidence_ref", ""),
        ("restart_recovery_evidence_ref", ""),
        ("desktop_projection_evidence_ref", ""),
        ("windows_msix_evidence_ref", ""),
        ("exact_head_ci_evidence_ref", ""),
        ("exact_master_ci_evidence_ref", ""),
        ("agent_execution_evidence_refs", []),
        ("agent_execution_evidence_bindings", {}),
        ("provider_tool_receipt_ids", []),
        ("output_artifact_sha256", "unknown"),
        ("output_validation_result", "NOT_VERIFIED"),
        ("cost_usage_evidence_ref", ""),
        ("human_owner_evidence_ref", ""),
        ("evidence_record_id", ""),
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


def test_final_closure_receipt_rejects_wrong_or_duplicate_agent_identities() -> None:
    receipt = _receipt()
    verified_agent_ids = _canonical_agent_ids()
    verified_agent_ids[-1] = "ilaios.agent.meta.not-canonical.v1"
    receipt["verified_agent_ids"] = verified_agent_ids
    with pytest.raises(AgentFinalClosureError, match="current canonical Agent identities"):
        validate_agent_final_closure_receipt(receipt)

    receipt = _receipt()
    verified_agent_ids = _canonical_agent_ids()
    verified_agent_ids[-1] = verified_agent_ids[0]
    receipt["verified_agent_ids"] = verified_agent_ids
    with pytest.raises(AgentFinalClosureError, match="duplicate Agent identities"):
        validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_rejects_incomplete_agent_evidence_coverage() -> None:
    receipt = _receipt()
    receipt["agent_execution_evidence_refs"] = ["evidence://exec-final-001/one-agent"]
    with pytest.raises(AgentFinalClosureError, match="cover every canonical Agent"):
        validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_rejects_unbound_or_reused_agent_evidence() -> None:
    receipt = _receipt()
    bindings = _agent_evidence_bindings()
    missing_agent = _canonical_agent_ids()[-1]
    del bindings[missing_agent]
    bindings["ilaios.agent.meta.not-canonical.v1"] = (
        "evidence://exec-final-001/ilaios.agent.meta.not-canonical.v1"
    )
    receipt["agent_execution_evidence_bindings"] = bindings
    with pytest.raises(
        AgentFinalClosureError,
        match="bind every canonical Agent exactly once",
    ):
        validate_agent_final_closure_receipt(receipt)

    receipt = _receipt()
    bindings = _agent_evidence_bindings()
    first, second = _canonical_agent_ids()[:2]
    bindings[second] = bindings[first]
    receipt["agent_execution_evidence_bindings"] = bindings
    with pytest.raises(AgentFinalClosureError, match="unique evidence refs"):
        validate_agent_final_closure_receipt(receipt)

    receipt = _receipt()
    bindings = _agent_evidence_bindings()
    first = _canonical_agent_ids()[0]
    bindings[first] = f"evidence://other-execution/{first}"
    receipt["agent_execution_evidence_bindings"] = bindings
    with pytest.raises(
        AgentFinalClosureError,
        match="exact execution and Agent identity",
    ):
        validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_rejects_malformed_lineage_sequences() -> None:
    receipt = _receipt()
    evidence_refs = _agent_evidence_refs()
    evidence_refs[-1] = ""
    receipt["agent_execution_evidence_refs"] = evidence_refs
    with pytest.raises(AgentFinalClosureError, match="agent_execution_evidence_refs"):
        validate_agent_final_closure_receipt(receipt)

    receipt = _receipt()
    receipt["provider_tool_receipt_ids"] = ["receipt-provider-001", 7]
    with pytest.raises(AgentFinalClosureError, match="provider_tool_receipt_ids"):
        validate_agent_final_closure_receipt(receipt)


def test_final_closure_receipt_cannot_disable_human_owner_requirement() -> None:
    receipt = _receipt()
    receipt["human_owner_required"] = False
    receipt["human_owner_state"] = "NOT_REQUIRED"
    with pytest.raises(AgentFinalClosureError, match="human-owner IndependentVerifier"):
        validate_agent_final_closure_receipt(receipt)
