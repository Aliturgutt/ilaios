"""Red-team proofs for canonical agent registry and readiness promotion."""

import pytest

from services.agent_readiness import (
    EXPECTED_AGENT_COUNT,
    AgentReadinessError,
    AgentReadinessProof,
    audit_agent_registry,
    effective_readiness,
    p0_registrations,
)
from services.agent_registry import (
    CANONICAL_AGENT_REGISTRY,
    RuntimeReadiness,
    registration_for,
)


def _proof(agent_id: str, **overrides: object) -> AgentReadinessProof:
    verifier_id = registration_for(agent_id).manifest.verifier_id
    values: dict[str, object] = {
        "agent_id": agent_id,
        "verifier_id": verifier_id,
        "invocation_passed": True,
        "skill_passed": True,
        "permission_passed": True,
        "provider_passed": True,
        "output_passed": True,
        "independent_verification_passed": True,
        "evidence_persisted": True,
        "desktop_projection_passed": True,
        "regression_e2e_passed": False,
        "evidence_digest": "a" * 64,
    }
    values.update(overrides)
    return AgentReadinessProof(**values)  # type: ignore[arg-type]


def test_registry_audit_locks_exact_47_identity_population() -> None:
    audit_agent_registry()
    assert len(CANONICAL_AGENT_REGISTRY) == EXPECTED_AGENT_COUNT == 47
    assert len(p0_registrations()) == 21
    assert {item.manifest.team for item in p0_registrations()} == {
        "core",
        "engineering",
        "security",
    }


def test_all_static_registrations_remain_registered_until_evidence() -> None:
    assert all(
        item.readiness is RuntimeReadiness.REGISTERED
        for item in CANONICAL_AGENT_REGISTRY
    )


def test_complete_execution_gates_promote_only_to_executable() -> None:
    proof = _proof("ilaios.agent.engineering.core.v1")
    assert effective_readiness(proof) is RuntimeReadiness.EXECUTABLE


def test_regression_e2e_is_required_for_verified() -> None:
    proof = _proof(
        "ilaios.agent.engineering.core.v1",
        regression_e2e_passed=True,
    )
    assert effective_readiness(proof) is RuntimeReadiness.VERIFIED


def test_missing_provider_proof_cannot_promote() -> None:
    proof = _proof(
        "ilaios.agent.engineering.core.v1",
        provider_passed=False,
        evidence_persisted=False,
        desktop_projection_passed=False,
        independent_verification_passed=False,
    )
    assert effective_readiness(proof) is RuntimeReadiness.REGISTERED


def test_wrong_verifier_fails_closed() -> None:
    proof = _proof(
        "ilaios.agent.security.codesec.v1",
        verifier_id="ilaios.agent.security.codesec.v1",
    )
    with pytest.raises(AgentReadinessError, match="verifier"):
        effective_readiness(proof)


def test_desktop_projection_cannot_precede_persisted_evidence() -> None:
    proof = _proof(
        "ilaios.agent.core.planner.v1",
        evidence_persisted=False,
        desktop_projection_passed=True,
    )
    with pytest.raises(AgentReadinessError, match="Desktop"):
        effective_readiness(proof)


def test_verified_cannot_be_claimed_with_malformed_evidence_digest() -> None:
    proof = _proof(
        "ilaios.agent.security.verifier.v1",
        regression_e2e_passed=True,
        evidence_digest="not-a-digest",
    )
    with pytest.raises(AgentReadinessError, match="SHA-256"):
        effective_readiness(proof)
