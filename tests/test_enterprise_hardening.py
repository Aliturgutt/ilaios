"""Tests for cross-cutting enterprise hardening gates."""

import pytest

from services.enterprise_hardening import (
    PROMOTED_FACTORY_IDS,
    EnterpriseHardeningError,
    HardeningEvidence,
    verify_promoted_factory_hardening,
)


def _evidence(capability_id: str, **overrides: bool) -> HardeningEvidence:
    values: dict[str, bool | str] = {
        "capability_id": capability_id,
        "recovery_verified": True,
        "isolation_verified": True,
        "provenance_verified": True,
        "observability_verified": True,
        "security_negative_tests_verified": True,
        "cost_boundary_verified": True,
        "stateful_persistence": False,
        "backup_restore_verified": False,
    }
    values.update(overrides)
    return HardeningEvidence(**values)  # type: ignore[arg-type]


def test_all_promoted_factories_have_bound_implementation_roots_and_accept_complete_evidence() -> None:
    for capability_id in PROMOTED_FACTORY_IDS:
        verify_promoted_factory_hardening(_evidence(capability_id))


def test_missing_cross_cutting_gate_fails_closed() -> None:
    with pytest.raises(EnterpriseHardeningError, match="missing hardening gates"):
        verify_promoted_factory_hardening(
            _evidence("ilaios.capability.personal-operations", observability_verified=False)
        )


def test_stateful_factory_requires_backup_restore_evidence() -> None:
    with pytest.raises(EnterpriseHardeningError, match="backup/restore evidence"):
        verify_promoted_factory_hardening(
            _evidence("ilaios.capability.research-data", stateful_persistence=True)
        )

    verify_promoted_factory_hardening(
        _evidence(
            "ilaios.capability.research-data",
            stateful_persistence=True,
            backup_restore_verified=True,
        )
    )


def test_unpromoted_capability_is_rejected() -> None:
    with pytest.raises(EnterpriseHardeningError, match="outside the promoted factory hardening set"):
        verify_promoted_factory_hardening(_evidence("ilaios.capability.core"))
