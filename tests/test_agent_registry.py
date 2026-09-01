"""Canonical ILAIOS agent-registry identity and admission proofs."""

from datetime import datetime, timedelta, timezone

from services.agent_governance import AgentInvocation, PermissionFirewall
from services.agent_registry import (
    CANONICAL_AGENT_REGISTRY,
    ORCHESTRATOR_ID,
    RuntimeReadiness,
    registration_for,
    registrations_for_team,
    validate_agent_registry,
)
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy

NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


def test_registry_has_stable_ilaios_machine_identity_and_named_engineering_team() -> None:
    validate_agent_registry()
    aliases = {item.manifest.alias for item in registrations_for_team("engineering")}
    assert {
        "Daedalus",
        "Hephaestus",
        "Apollo",
        "Atlas",
        "Integration Bridge",
        "Dike",
        "Athena",
        "Argus",
        "Janus",
        "Asclepius",
    } <= aliases
    assert all(
        item.manifest.agent_id.startswith("ilaios.agent.")
        for item in CANONICAL_AGENT_REGISTRY
    )
    assert all(
        legacy not in item.manifest.agent_id.casefold()
        for item in CANONICAL_AGENT_REGISTRY
        for legacy in ("hermes", "ilakos", "ilaten")
    )


def test_security_team_preserves_coordinator_native_specialists_and_verifier() -> None:
    security = registrations_for_team("security")
    aliases = {item.manifest.alias for item in security}
    assert aliases == {
        "SecurityCoordinator",
        "CodeSec",
        "WebAPISec",
        "SupplyChainSec",
        "InfrastructureSec",
        "SecurityVerifier",
    }
    assert all(item.readiness is RuntimeReadiness.REGISTERED for item in security)
    assert all(item.manifest.verifier_id != item.manifest.agent_id for item in security)


def test_registered_codesec_manifest_is_admissible_only_with_scoped_grant() -> None:
    registration = registration_for("ilaios.agent.security.codesec.v1")
    manifest = registration.manifest
    policy = GrantPolicy()
    firewall = PermissionFirewall((manifest,), policy)
    grant = ExecutionGrant(
        "grant-codesec",
        manifest.agent_id,
        frozenset({"repository.read"}),
        frozenset({manifest.agent_id}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )
    invocation = AgentInvocation(
        invocation_id="invoke-codesec",
        caller_id=ORCHESTRATOR_ID,
        target_id=manifest.agent_id,
        capability="security.sast",
        permission="repository.read",
        input_class="governed_task",
        requested_output_class="proposal",
        prompt="Review the authorized repository scope and propose findings.",
        security_scan_passed=True,
    )
    evidence = firewall.admit(invocation, grant, NOW)
    assert evidence.agent_id == manifest.agent_id
    assert evidence.verifier_id == "ilaios.agent.security.verifier.v1"


def test_registry_does_not_claim_specialized_executors_are_verified() -> None:
    assert CANONICAL_AGENT_REGISTRY
    assert all(
        item.readiness is RuntimeReadiness.REGISTERED
        for item in CANONICAL_AGENT_REGISTRY
    )
