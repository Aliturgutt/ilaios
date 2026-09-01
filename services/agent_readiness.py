"""Evidence-gated readiness and canonical registry audit for ILAIOS agents.

This module deliberately does not mutate the canonical agent registry. Registry
presence proves identity/governance only. Effective EXECUTABLE/VERIFIED state is
derived from explicit runtime/evidence gates so a code edit cannot self-promote
an agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.agent_registry import (
    CANONICAL_AGENT_REGISTRY,
    AgentRegistration,
    RuntimeReadiness,
    registration_for,
)
from services.capability_registry import CAPABILITIES


class AgentReadinessError(ValueError):
    """Canonical registry or readiness evidence failed closed."""


EXPECTED_TEAM_COUNTS = {
    "core": 5,
    "engineering": 10,
    "security": 6,
    "web": 6,
    "media": 8,
    "intelligence": 4,
    "operations": 6,
    "meta": 2,
}
EXPECTED_AGENT_COUNT = sum(EXPECTED_TEAM_COUNTS.values())
P0_TEAMS = frozenset({"core", "engineering", "security"})
LEGACY_IDENTITY_TOKENS = frozenset(
    source.casefold()
    for capability in CAPABILITIES
    for source in capability.legacy_sources
)

KNOWN_BACKING_CAPABILITIES = frozenset(
    {
        "control-plane",
        "governance",
        "ai-governance",
        "software-factory",
        "validation",
        "observability",
        "deployment",
        "operations",
        "agent-governance",
        "web-factory",
        "video-factory",
        "knowledge",
        "runtime-routing",
    }
)


@dataclass(frozen=True, slots=True)
class AgentReadinessProof:
    agent_id: str
    verifier_id: str
    invocation_passed: bool = False
    skill_passed: bool = False
    permission_passed: bool = False
    provider_passed: bool = False
    output_passed: bool = False
    independent_verification_passed: bool = False
    evidence_persisted: bool = False
    desktop_projection_passed: bool = False
    regression_e2e_passed: bool = False
    evidence_digest: str = ""

    @property
    def executable_gates_passed(self) -> bool:
        return all(
            (
                self.invocation_passed,
                self.skill_passed,
                self.permission_passed,
                self.provider_passed,
                self.output_passed,
                self.independent_verification_passed,
                self.evidence_persisted,
                self.desktop_projection_passed,
            )
        )


def p0_registrations() -> tuple[AgentRegistration, ...]:
    return tuple(
        item for item in CANONICAL_AGENT_REGISTRY if item.manifest.team in P0_TEAMS
    )


def audit_agent_registry(
    registrations: tuple[AgentRegistration, ...] = CANONICAL_AGENT_REGISTRY,
) -> None:
    if len(registrations) != EXPECTED_AGENT_COUNT:
        raise AgentReadinessError(
            f"canonical agent count mismatch: expected={EXPECTED_AGENT_COUNT} actual={len(registrations)}"
        )
    ids = [item.manifest.agent_id for item in registrations]
    if len(ids) != len(set(ids)):
        raise AgentReadinessError("duplicate canonical agent ID")
    team_counts = {
        team: sum(item.manifest.team == team for item in registrations)
        for team in EXPECTED_TEAM_COUNTS
    }
    if team_counts != EXPECTED_TEAM_COUNTS:
        raise AgentReadinessError(f"canonical team composition mismatch: {team_counts!r}")
    for item in registrations:
        manifest = item.manifest
        if not manifest.agent_id.startswith("ilaios.agent."):
            raise AgentReadinessError("agent ID is outside canonical ILAIOS namespace")
        if any(
            legacy in manifest.agent_id.casefold()
            for legacy in LEGACY_IDENTITY_TOKENS
        ):
            raise AgentReadinessError("legacy identity leaked into machine agent ID")
        if not manifest.capabilities or not manifest.permissions:
            raise AgentReadinessError(
                f"agent has empty capability/permission boundary: {manifest.agent_id}"
            )
        if manifest.verifier_id == manifest.agent_id:
            raise AgentReadinessError("agent cannot independently verify itself")
        if item.backing_capability not in KNOWN_BACKING_CAPABILITIES:
            raise AgentReadinessError(
                f"unknown backing capability for {manifest.agent_id}: {item.backing_capability}"
            )
        if manifest.dependencies != frozenset({item.backing_capability}):
            raise AgentReadinessError(
                f"backing capability/dependency mismatch for {manifest.agent_id}"
            )
        if item.readiness != RuntimeReadiness.REGISTERED:
            raise AgentReadinessError(
                f"static readiness promotion is prohibited: {manifest.agent_id}"
            )
    if len(p0_registrations()) != 21:
        raise AgentReadinessError("P0 population must contain exactly 21 agents")


def effective_readiness(proof: AgentReadinessProof) -> RuntimeReadiness:
    registration = registration_for(proof.agent_id)
    expected_verifier = registration.manifest.verifier_id
    if proof.verifier_id != expected_verifier:
        raise AgentReadinessError("readiness proof verifier does not match manifest")
    if proof.verifier_id == proof.agent_id:
        raise AgentReadinessError("producer cannot verify its own readiness proof")
    if proof.independent_verification_passed and not proof.output_passed:
        raise AgentReadinessError("verification cannot precede a successful output")
    if proof.evidence_persisted and not proof.independent_verification_passed:
        raise AgentReadinessError(
            "verified evidence cannot be persisted before independent verification"
        )
    if proof.desktop_projection_passed and not proof.evidence_persisted:
        raise AgentReadinessError("Desktop cannot project unpersisted agent evidence")
    if proof.regression_e2e_passed and not proof.executable_gates_passed:
        raise AgentReadinessError("regression/E2E cannot bypass executable gates")
    if not proof.executable_gates_passed:
        return RuntimeReadiness.REGISTERED
    if not proof.evidence_digest or len(proof.evidence_digest) != 64:
        raise AgentReadinessError(
            "executable readiness requires SHA-256 evidence digest"
        )
    if any(
        character not in "0123456789abcdef" for character in proof.evidence_digest
    ):
        raise AgentReadinessError("evidence digest must be lowercase SHA-256 hex")
    if proof.regression_e2e_passed:
        return RuntimeReadiness.VERIFIED
    return RuntimeReadiness.EXECUTABLE


audit_agent_registry()
