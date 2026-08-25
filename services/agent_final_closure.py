"""Fail-closed validator for the canonical ILAIOS Agent final closure receipt.

This module is evidence validation only. It does not execute agents, mutate
readiness, replace governance/runtime authorities, or synthesize evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from services.agent_readiness import EXPECTED_AGENT_COUNT, EXPECTED_TEAM_COUNTS
from services.agent_registry import CANONICAL_AGENT_REGISTRY

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_RESULTS = (
    "registry_identity_result",
    "runtime_state_truth_result",
    "runtime_e2e_result",
    "family_runtime_execution_result",
    "provider_tool_execution_result",
    "provider_tool_receipt_binding_result",
    "browser_tool_egress_security_result",
    "g1_security_result",
    "evidence_integrity_result",
    "execution_evidence_lineage_result",
    "cross_tenant_artifact_evidence_substitution_result",
    "cost_usage_truth_result",
    "tenant_bound_cost_usage_result",
    "restart_recovery_result",
    "operations_meta_runtime_result",
    "desktop_projection_result",
    "windows_msix_packaged_runtime_result",
    "cross_client_identity_tenant_result",
    "exact_head_release_governance_result",
    "exact_master_release_governance_result",
)
_REQUIRED_G1_ADVERSARIAL_VERDICTS = (
    "approval_replay",
    "wrong_action",
    "wrong_tenant",
    "expired_grant",
    "revoked_grant",
    "direct_tool_gateway_bypass",
    "forged_provider_success",
    "forged_evidence",
    "forged_approval",
    "forged_tool_result",
    "kill_switch",
    "unavailable_agent",
    "suspended_agent",
    "retired_agent",
    "out_of_manifest_permission",
    "out_of_manifest_capability",
    "out_of_manifest_input",
    "secret_bearing_input",
    "unapproved_egress",
    "exhausted_budget",
    "cross_tenant_artifact_evidence_substitution",
)
_REQUIRED_NONEMPTY_STRINGS = (
    "execution_id",
    "job_id",
    "user_id",
    "tenant_id",
    "session_id",
    "skill_route",
    "tool_route",
    "provider_route",
    "runtime_e2e_evidence_ref",
    "g1_security_evidence_ref",
    "evidence_integrity_evidence_ref",
    "restart_recovery_evidence_ref",
    "desktop_projection_evidence_ref",
    "windows_msix_evidence_ref",
    "exact_head_ci_evidence_ref",
    "exact_master_ci_evidence_ref",
    "cost_usage_evidence_ref",
    "human_owner_evidence_ref",
    "evidence_record_id",
    "output_artifact_evidence_ref",
)
_REQUIRED_NONEMPTY_SEQUENCES = (
    "agent_execution_evidence_refs",
    "provider_tool_receipt_ids",
)
_CONTEXT_KEYS = ("execution_id", "job_id", "user_id", "tenant_id", "session_id")


class AgentFinalClosureError(ValueError):
    """Final Agent closure evidence is incomplete, inconsistent, or stale."""


def _require_verified_result(receipt: Mapping[str, object], key: str) -> None:
    if receipt.get(key) != "VERIFIED":
        raise AgentFinalClosureError(f"{key} must be VERIFIED")


def _require_g1_adversarial_verdicts(receipt: Mapping[str, object]) -> None:
    value = receipt.get("g1_adversarial_verdicts")
    if not isinstance(value, Mapping):
        raise AgentFinalClosureError("g1_adversarial_verdicts must be a mapping")
    normalized = {str(key): verdict for key, verdict in value.items()}
    required = set(_REQUIRED_G1_ADVERSARIAL_VERDICTS)
    if set(normalized) != required:
        raise AgentFinalClosureError(
            "g1_adversarial_verdicts must contain the complete canonical negative-case matrix"
        )
    failed = sorted(
        key for key in _REQUIRED_G1_ADVERSARIAL_VERDICTS if normalized.get(key) != "VERIFIED DENY"
    )
    if failed:
        raise AgentFinalClosureError(
            "all mandatory G1 adversarial verdicts must be VERIFIED DENY"
        )


def _require_nonempty_string(receipt: Mapping[str, object], key: str) -> None:
    value = receipt.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AgentFinalClosureError(f"{key} must be a non-empty string")


def _require_nonempty_string_sequence(receipt: Mapping[str, object], key: str) -> None:
    value = receipt.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise AgentFinalClosureError(f"{key} must be a non-empty sequence")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise AgentFinalClosureError(f"{key} must contain only non-empty strings")


def _require_exact_canonical_agent_identities(receipt: Mapping[str, object]) -> None:
    value = receipt.get("verified_agent_ids")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise AgentFinalClosureError("verified_agent_ids must be a non-empty sequence")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise AgentFinalClosureError("verified_agent_ids must contain only non-empty strings")
    verified_ids = tuple(str(item) for item in value)
    canonical_ids = tuple(item.manifest.agent_id for item in CANONICAL_AGENT_REGISTRY)
    if len(verified_ids) != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("verified_agent_ids must contain every canonical Agent exactly once")
    if len(set(verified_ids)) != len(verified_ids):
        raise AgentFinalClosureError("verified_agent_ids contains duplicate Agent identities")
    if set(verified_ids) != set(canonical_ids):
        raise AgentFinalClosureError("verified_agent_ids does not match current canonical Agent identities")


def _require_agent_evidence_bindings(receipt: Mapping[str, object]) -> dict[str, str]:
    value = receipt.get("agent_execution_evidence_bindings")
    if not isinstance(value, Mapping):
        raise AgentFinalClosureError("agent_execution_evidence_bindings must be a mapping")

    canonical_ids = {item.manifest.agent_id for item in CANONICAL_AGENT_REGISTRY}
    normalized: dict[str, str] = {}
    for key, evidence_ref in value.items():
        agent_id = str(key)
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise AgentFinalClosureError(
                "agent_execution_evidence_bindings must contain non-empty evidence refs"
            )
        normalized[agent_id] = evidence_ref.strip()

    if set(normalized) != canonical_ids:
        raise AgentFinalClosureError(
            "agent_execution_evidence_bindings must bind every canonical Agent exactly once"
        )
    if len(set(normalized.values())) != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError(
            "agent_execution_evidence_bindings must use unique evidence refs per canonical Agent"
        )

    execution_id = receipt.get("execution_id")
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise AgentFinalClosureError(
            "execution_id must be present before validating Agent evidence bindings"
        )
    for agent_id, evidence_ref in normalized.items():
        if execution_id not in evidence_ref or agent_id not in evidence_ref:
            raise AgentFinalClosureError(
                "Agent evidence bindings must include the exact execution and Agent identity"
            )
    return normalized


def _require_evidence_context_bindings(
    receipt: Mapping[str, object], *, evidence_refs: Sequence[str]
) -> None:
    value = receipt.get("evidence_context_bindings")
    if not isinstance(value, Mapping):
        raise AgentFinalClosureError("evidence_context_bindings must be a mapping")

    required_refs = set(evidence_refs)
    provider_receipts = receipt.get("provider_tool_receipt_ids")
    if isinstance(provider_receipts, Sequence) and not isinstance(provider_receipts, (str, bytes)):
        required_refs.update(
            str(item).strip()
            for item in provider_receipts
            if isinstance(item, str) and item.strip()
        )
    output_evidence_ref = receipt.get("output_artifact_evidence_ref")
    if isinstance(output_evidence_ref, str) and output_evidence_ref.strip():
        required_refs.add(output_evidence_ref.strip())

    normalized: dict[str, Mapping[object, object]] = {}
    for raw_ref, raw_context in value.items():
        ref = str(raw_ref).strip()
        if not ref or not isinstance(raw_context, Mapping):
            raise AgentFinalClosureError(
                "evidence_context_bindings must map non-empty evidence refs to context mappings"
            )
        normalized[ref] = raw_context

    if set(normalized) != required_refs:
        raise AgentFinalClosureError(
            "evidence_context_bindings must cover exactly all Agent evidence and provider/tool/output receipts"
        )

    expected = {key: receipt.get(key) for key in _CONTEXT_KEYS}
    for context in normalized.values():
        if {str(key) for key in context} != set(_CONTEXT_KEYS):
            raise AgentFinalClosureError(
                "evidence context must contain exact execution/job/user/tenant/session keys"
            )
        for key, expected_value in expected.items():
            if context.get(key) != expected_value:
                raise AgentFinalClosureError(
                    "evidence context is stale, cross-job, cross-user, cross-tenant, or cross-session"
                )


def _require_evidence_revision_bindings(
    receipt: Mapping[str, object],
    *,
    exact_head_sha: str,
    exact_master_sha: str,
    agent_evidence_refs: Sequence[str],
) -> None:
    value = receipt.get("evidence_revision_bindings")
    if not isinstance(value, Mapping):
        raise AgentFinalClosureError("evidence_revision_bindings must be a mapping")

    normalized: dict[str, str] = {}
    for evidence_ref, revision_sha in value.items():
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise AgentFinalClosureError(
                "evidence_revision_bindings must use non-empty evidence references"
            )
        if not isinstance(revision_sha, str) or _SHA40.fullmatch(revision_sha) is None:
            raise AgentFinalClosureError(
                "evidence_revision_bindings must bind references to lowercase 40-hex SHAs"
            )
        normalized[evidence_ref.strip()] = revision_sha

    exact_head_ref = receipt.get("exact_head_ci_evidence_ref")
    if not isinstance(exact_head_ref, str) or not exact_head_ref.strip():
        raise AgentFinalClosureError("exact_head_ci_evidence_ref must be present")
    if normalized.get(exact_head_ref.strip()) != exact_head_sha:
        raise AgentFinalClosureError("exact-head CI evidence is not bound to exact_head_sha")

    master_bound_refs: set[str] = set(agent_evidence_refs)
    for key in (
        "runtime_e2e_evidence_ref",
        "g1_security_evidence_ref",
        "evidence_integrity_evidence_ref",
        "restart_recovery_evidence_ref",
        "desktop_projection_evidence_ref",
        "windows_msix_evidence_ref",
        "exact_master_ci_evidence_ref",
        "cost_usage_evidence_ref",
        "human_owner_evidence_ref",
        "evidence_record_id",
        "output_artifact_evidence_ref",
    ):
        evidence_ref = receipt.get(key)
        if isinstance(evidence_ref, str) and evidence_ref.strip():
            master_bound_refs.add(evidence_ref.strip())

    provider_receipts = receipt.get("provider_tool_receipt_ids")
    if isinstance(provider_receipts, Sequence) and not isinstance(provider_receipts, (str, bytes)):
        master_bound_refs.update(
            str(item).strip()
            for item in provider_receipts
            if isinstance(item, str) and item.strip()
        )

    missing = sorted(ref for ref in master_bound_refs if ref not in normalized)
    if missing:
        raise AgentFinalClosureError("final closure evidence is missing exact-master revision bindings")
    stale = sorted(ref for ref in master_bound_refs if normalized.get(ref) != exact_master_sha)
    if stale:
        raise AgentFinalClosureError("final closure evidence contains stale or cross-SHA bindings")


def _require_output_artifact_evidence_binding(receipt: Mapping[str, object]) -> None:
    value = receipt.get("output_artifact_evidence_binding")
    if not isinstance(value, Mapping):
        raise AgentFinalClosureError("output_artifact_evidence_binding must be a mapping")
    if {str(key) for key in value} != {"evidence_ref", "sha256"}:
        raise AgentFinalClosureError(
            "output_artifact_evidence_binding must contain exact evidence_ref and sha256 keys"
        )
    evidence_ref = receipt.get("output_artifact_evidence_ref")
    artifact_sha = receipt.get("output_artifact_sha256")
    if value.get("evidence_ref") != evidence_ref or value.get("sha256") != artifact_sha:
        raise AgentFinalClosureError(
            "output artifact evidence must bind the exact evidence ref to the exact artifact SHA-256"
        )


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
    exact_head_sha = receipt.get("exact_head_sha")
    if not isinstance(exact_head_sha, str) or _SHA40.fullmatch(exact_head_sha) is None:
        raise AgentFinalClosureError("exact_head_sha must be lowercase 40-hex")

    canonical_count = receipt.get("canonical_agent_count")
    verified_count = receipt.get("verified_agent_count")
    if canonical_count != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("canonical Agent count does not match current source")
    if verified_count != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("all canonical Agents are not VERIFIED")
    _require_exact_canonical_agent_identities(receipt)

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
    _require_g1_adversarial_verdicts(receipt)

    for key in _REQUIRED_NONEMPTY_STRINGS:
        _require_nonempty_string(receipt, key)
    for key in _REQUIRED_NONEMPTY_SEQUENCES:
        _require_nonempty_string_sequence(receipt, key)
    normalized_bindings = _require_agent_evidence_bindings(receipt)

    agent_execution_evidence_refs = receipt.get("agent_execution_evidence_refs")
    if not isinstance(agent_execution_evidence_refs, Sequence) or isinstance(
        agent_execution_evidence_refs, (str, bytes)
    ):
        raise AgentFinalClosureError("agent_execution_evidence_refs must be a sequence")
    normalized_refs = tuple(str(item).strip() for item in agent_execution_evidence_refs)
    if len(normalized_refs) != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError(
            "agent_execution_evidence_refs must contain exactly one ref per canonical Agent"
        )
    if len(set(normalized_refs)) != EXPECTED_AGENT_COUNT:
        raise AgentFinalClosureError("agent_execution_evidence_refs must be unique")
    if set(normalized_refs) != set(normalized_bindings.values()):
        raise AgentFinalClosureError(
            "agent_execution_evidence_refs must exactly match canonical Agent evidence bindings"
        )

    _require_evidence_context_bindings(receipt, evidence_refs=normalized_refs)
    _require_evidence_revision_bindings(
        receipt,
        exact_head_sha=exact_head_sha,
        exact_master_sha=revision_sha,
        agent_evidence_refs=normalized_refs,
    )

    output_artifact_sha256 = receipt.get("output_artifact_sha256")
    if (
        not isinstance(output_artifact_sha256, str)
        or _SHA256.fullmatch(output_artifact_sha256) is None
    ):
        raise AgentFinalClosureError("output_artifact_sha256 must be lowercase SHA-256")
    _require_output_artifact_evidence_binding(receipt)

    if receipt.get("output_validation_result") != "VERIFIED":
        raise AgentFinalClosureError("output_validation_result must be VERIFIED")

    human_owner_required = receipt.get("human_owner_required")
    human_owner_state = receipt.get("human_owner_state")
    if human_owner_required is not True:
        raise AgentFinalClosureError(
            "final Agent closure requires human-owner IndependentVerifier evidence"
        )
    if human_owner_state != "VERIFIED":
        raise AgentFinalClosureError("required human-owner IndependentVerifier is not VERIFIED")

    blockers = receipt.get("remaining_external_blockers")
    if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes)):
        raise AgentFinalClosureError("remaining_external_blockers must be a sequence")
    if len(blockers) != 0:
        raise AgentFinalClosureError("Agent closure still has external blockers")

    evidence_digest = receipt.get("closure_evidence_sha256")
    if not isinstance(evidence_digest, str) or _SHA256.fullmatch(evidence_digest) is None:
        raise AgentFinalClosureError("closure_evidence_sha256 must be lowercase SHA-256")
