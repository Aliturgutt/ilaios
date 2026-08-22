from __future__ import annotations

# Final Agent closure exact-master recertification trigger; no test behavior change.
# Agent closure exact-master co-certification trigger; no test behavior change.
# Final current-master Operations/Meta recertification trigger; no test behavior change.
import pytest

from services.agent_registry import INDEPENDENT_VERIFIER_ID, registration_for
from services.independent_verifier_execution import INDEPENDENT_VERIFIER_PROVIDER_ID
from services.operations_meta_agent_execution import (
    OPERATIONS_META_AGENT_BINDINGS,
    OPERATIONS_META_GOVERNED_AI_CAPABILITIES,
)
from services.operations_meta_agent_live_certification import (
    OperationsMetaAgentLiveCertificationError,
    _assert_independent_verifier_routes_are_structural,
    _invocation,
    _verified_proof,
)


def test_live_certification_has_seven_provider_agents_and_one_independent_verifier() -> None:
    governed = [item for item in OPERATIONS_META_AGENT_BINDINGS if item.execution_mode == "governed-ai"]
    independent = [
        item for item in OPERATIONS_META_AGENT_BINDINGS if item.execution_mode == "independent-verification"
    ]
    assert len(governed) == 7
    assert len(independent) == 1
    assert independent[0].agent_id == INDEPENDENT_VERIFIER_ID
    assert independent[0].capability == "evidence.verify"
    assert "evidence.verify" not in OPERATIONS_META_GOVERNED_AI_CAPABILITIES


def test_independent_verifier_remains_human_owner_verified() -> None:
    verifier = registration_for(INDEPENDENT_VERIFIER_ID)
    assert verifier.manifest.verifier_id == "human.owner"


def test_provider_live_probe_is_egress_and_dlp_bounded() -> None:
    binding = next(item for item in OPERATIONS_META_AGENT_BINDINGS if item.execution_mode == "governed-ai")
    invocation = _invocation(
        binding.agent_id,
        binding.capability,
        binding.permission,
        prompt="bounded certification proposal",
    )
    assert invocation.target_id == binding.agent_id
    assert invocation.capability == binding.capability
    assert invocation.permission == binding.permission
    assert invocation.external_egress is True
    assert invocation.dlp_approved is True
    assert invocation.security_scan_passed is True
    assert invocation.requested_output_class == "proposal"


def test_provider_readiness_proof_uses_manifest_verifier() -> None:
    binding = next(item for item in OPERATIONS_META_AGENT_BINDINGS if item.execution_mode == "governed-ai")
    proof = _verified_proof(binding.agent_id, "a" * 64)
    assert proof.verifier_id == INDEPENDENT_VERIFIER_ID
    assert proof.independent_verification_passed is True
    assert proof.evidence_persisted is True
    assert proof.desktop_projection_passed is True
    assert proof.regression_e2e_passed is True


def test_structural_verifier_routes_are_not_mislabeled_as_generic_provider_execution() -> None:
    routes = tuple(
        {
            "agent_id": INDEPENDENT_VERIFIER_ID,
            "provider_id": INDEPENDENT_VERIFIER_PROVIDER_ID,
        }
        for _ in range(7)
    )
    _assert_independent_verifier_routes_are_structural(routes)


def test_independent_verifier_rejects_non_structural_provider_route() -> None:
    routes = tuple(
        {
            "agent_id": INDEPENDENT_VERIFIER_ID,
            "provider_id": (
                "openrouter" if index == 6 else INDEPENDENT_VERIFIER_PROVIDER_ID
            ),
        }
        for index in range(7)
    )
    with pytest.raises(
        OperationsMetaAgentLiveCertificationError,
        match="escaped deterministic structural attestation boundary",
    ):
        _assert_independent_verifier_routes_are_structural(routes)
