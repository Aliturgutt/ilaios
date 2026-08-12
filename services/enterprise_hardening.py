"""Cross-cutting enterprise hardening gate for promoted ILAIOS factories."""

from __future__ import annotations

from dataclasses import dataclass

from services.capability_registry import capability


class EnterpriseHardeningError(PermissionError):
    """A promoted factory is missing required enterprise hardening evidence."""


PROMOTED_FACTORY_IDS = (
    "ilaios.capability.security-factory",
    "ilaios.capability.research-data",
    "ilaios.capability.creative-document",
    "ilaios.capability.commerce-growth",
    "ilaios.capability.personal-operations",
    "ilaios.capability.app-factory",
)


@dataclass(frozen=True, slots=True)
class HardeningEvidence:
    capability_id: str
    recovery_verified: bool
    isolation_verified: bool
    provenance_verified: bool
    observability_verified: bool
    security_negative_tests_verified: bool
    cost_boundary_verified: bool
    stateful_persistence: bool = False
    backup_restore_verified: bool = False


def verify_promoted_factory_hardening(evidence: HardeningEvidence) -> None:
    """Fail closed unless a promoted factory has all applicable hardening gates."""
    if evidence.capability_id not in PROMOTED_FACTORY_IDS:
        raise EnterpriseHardeningError("capability is outside the promoted factory hardening set")

    definition = capability(evidence.capability_id)
    if definition.domain != "factory" or not definition.implementation_roots:
        raise EnterpriseHardeningError("factory requires a bound implementation root")

    required = {
        "recovery": evidence.recovery_verified,
        "isolation": evidence.isolation_verified,
        "provenance": evidence.provenance_verified,
        "observability": evidence.observability_verified,
        "security_negative_tests": evidence.security_negative_tests_verified,
        "cost_boundary": evidence.cost_boundary_verified,
    }
    missing = sorted(name for name, passed in required.items() if not passed)
    if missing:
        raise EnterpriseHardeningError(f"missing hardening gates: {missing}")

    if evidence.stateful_persistence and not evidence.backup_restore_verified:
        raise EnterpriseHardeningError("stateful persistence requires backup/restore evidence")
