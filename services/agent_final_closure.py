"""Fail-closed validator for the canonical ILAIOS Agent final closure receipt.

This module is evidence validation only. It does not execute agents, mutate
readiness, replace governance/runtime authorities, or synthesize evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from services.agent_readiness import EXPECTED_AGENT_COUNT, EXPECTED_TEAM_COUNTS

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_RESULTS = (
    "runtime_e2e_result",
    "provider_tool_execution_result",
    "provider_tool_receipt_binding_result",
    "g1_security_result",
    "evidence_integrity_result",
    "execution_evidence_lineage_result",
    "cross_tenant_artifact_evidence_substitution_result",
    "cost_usage_truth_result",
    "tenant_bound_cost_usage_result",
    "restart_recovery_result",
    "desktop_projection_result",
    "windows_msix_packaged_runtime_result",
    "cross_client_identity_tenant_result",
    "exact_head_release_governance_result",
    "exact_master_release_governance_result",
)


class AgentFinalClosureError(ValueError):
    """Final Agent closure evidence is incomplete, inconsistent, or stale."""


def _require_verified_result(receipt: Mapping[str, object], key: str) -> None:
    if receipt.get(key) != "VERIFIED":
        raise AgentFinalClosureError(f"{key} must be VERIFIED")


def validate_agent_final_closure_receipt(receipt: Mapping[str, object]) -> None:
    """Validate that a receipt is sufficient for full Agent workstream closure.

    The caller must provide evidence-derived values. This validator deliberately
    refuses PARTIAL/BLOCKED/NOT_VERIFIED values and cannot create evidence.
    """

    if receipt.get("agent_workstream") != "CLOSED":
        raise AgentFinalClosureError("agent workstream is not CLOSED")

    revision_sha = receipt.get("exact_master_sha")
    if not isinstance(revision_sha, str) or _SHA40.fullmatch(revision_sha) is None:
        raise AgentFinalClosureError("exact_master_sha must be lowercase 40-hex")

    canonical_count = receipt.get("canonical_agent_count")
    verified_count = receipt.get("verified_agent_count")
    if canonical_count != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("canonical Agent count does not match current source")
    if verified_count != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("all canonical Agents are not VERIFIED")

    runtime_active_count = receipt.get("runtime_active_count")
    if not isinstance(runtime_active_count, int) or isinstance(runtime_active_count, bool):
        raise AgentFinalClosureError("runtime_active_count must be an integer")
    if runtime_active_count < 1 or runtime_active_count > EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("runtime_active_count is outside canonical bounds")

    family_breakdown = receipt.get("verified_family_breakdown")
    if not isinstance(family_breakdown, Mapping):
        raise AgentFinalClosureError("verified_family_breakdown is required")
    normalized_breakdown = {str(key): value for key, value in family_breakdown.items()}
    if normalized_breakdown != EXPECTED_TEAM_COUNTS:
        raise AgentFinalClosureError("verified family breakdown does not match canonical source")

    for key in _REQUIRED_RESULTS:
        _require_verified_result(receipt, key)

    human_owner_required = receipt.get("human_owner_required")
    human_owner_state = receipt.get("human_owner_state")
    if human_owner_required is True and human_owner_state != "VERIFIED":
        raise AgentFinalClosureError("required human-owner IndependentVerifier is not VERIFIED")
    if human_owner_required not in (True, False):
        raise AgentFinalClosureError("human_owner_required must be boolean")

    blockers = receipt.get("remaining_external_blockers")
    if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes)):
        raise AgentFinalClosureError("remaining_external_blockers must be a sequence")
    if len(blockers) != 0:
        raise AgentFinalClosureError("Agent closure still has external blockers")

    evidence_digest = receipt.get("closure_evidence_sha256")
    if not isinstance(evidence_digest, str) or re.fullmatch(r"[0-9a-f]{64}", evidence_digest) is None:
        raise AgentFinalClosureError("closure_evidence_sha256 must be lowercase SHA-256")
