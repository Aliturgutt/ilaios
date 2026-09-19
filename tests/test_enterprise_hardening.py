"""Tests for cross-cutting enterprise hardening gates."""

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from services.enterprise_hardening import (
    HARDENING_GATES,
    PROMOTED_FACTORY_IDS,
    EnterpriseHardeningError,
    HardeningEvidence,
    HardeningReceipt,
    record_hardening_receipt,
    verify_promoted_factory_hardening,
)
from services.evidence.store import EvidenceStore

_SOURCE_REVISION = "a" * 40
_OTHER_REVISION = "b" * 40


def _evidence(
    capability_id: str,
    *,
    source_revision: str = _SOURCE_REVISION,
    receipts: tuple[HardeningReceipt, ...] = (),
    recovery_verified: bool = True,
    isolation_verified: bool = True,
    provenance_verified: bool = True,
    observability_verified: bool = True,
    security_negative_tests_verified: bool = True,
    cost_boundary_verified: bool = True,
    stateful_persistence: bool = False,
    backup_restore_verified: bool = False,
) -> HardeningEvidence:
    return HardeningEvidence(
        capability_id=capability_id,
        recovery_verified=recovery_verified,
        isolation_verified=isolation_verified,
        provenance_verified=provenance_verified,
        observability_verified=observability_verified,
        security_negative_tests_verified=security_negative_tests_verified,
        cost_boundary_verified=cost_boundary_verified,
        stateful_persistence=stateful_persistence,
        backup_restore_verified=backup_restore_verified,
        source_revision=source_revision,
        receipts=receipts,
    )


def _receipts(
    store: EvidenceStore,
    capability_id: str,
    *,
    source_revision: str = _SOURCE_REVISION,
    stateful: bool = False,
    failed_gate: str | None = None,
) -> tuple[HardeningReceipt, ...]:
    gates = list(HARDENING_GATES)
    if stateful:
        gates.append("backup_restore")
    return tuple(
        record_hardening_receipt(
            store,
            capability_id=capability_id,
            gate=gate,
            source_revision=source_revision,
            passed=gate != failed_gate,
        )
        for gate in gates
    )


def _complete_evidence(
    store: EvidenceStore,
    capability_id: str,
    *,
    stateful: bool = False,
) -> HardeningEvidence:
    return _evidence(
        capability_id,
        receipts=_receipts(store, capability_id, stateful=stateful),
        stateful_persistence=stateful,
        backup_restore_verified=stateful,
    )


def test_all_promoted_factories_require_and_accept_bound_immutable_receipts(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    for capability_id in PROMOTED_FACTORY_IDS:
        verify_promoted_factory_hardening(
            _complete_evidence(store, capability_id),
            store=store,
        )


def test_boolean_self_assertion_without_receipts_fails_closed(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    with pytest.raises(
        EnterpriseHardeningError,
        match="missing immutable hardening receipts",
    ):
        verify_promoted_factory_hardening(
            _evidence("ilaios.capability.personal-operations"),
            store=store,
        )


def test_missing_cross_cutting_boolean_gate_still_fails_closed(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    evidence = _complete_evidence(store, "ilaios.capability.personal-operations")
    with pytest.raises(EnterpriseHardeningError, match="missing hardening gates"):
        verify_promoted_factory_hardening(
            replace(evidence, observability_verified=False),
            store=store,
        )


def test_stateful_factory_requires_boolean_and_receipt_backup_restore_evidence(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    base_receipts = _receipts(store, "ilaios.capability.research-data")

    with pytest.raises(EnterpriseHardeningError, match="backup/restore evidence"):
        verify_promoted_factory_hardening(
            _evidence(
                "ilaios.capability.research-data",
                receipts=base_receipts,
                stateful_persistence=True,
            ),
            store=store,
        )

    with pytest.raises(
        EnterpriseHardeningError,
        match="missing immutable hardening receipts",
    ):
        verify_promoted_factory_hardening(
            _evidence(
                "ilaios.capability.research-data",
                receipts=base_receipts,
                stateful_persistence=True,
                backup_restore_verified=True,
            ),
            store=store,
        )

    verify_promoted_factory_hardening(
        _complete_evidence(store, "ilaios.capability.research-data", stateful=True),
        store=store,
    )


def test_unpromoted_capability_is_rejected(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    with pytest.raises(
        EnterpriseHardeningError,
        match="outside the promoted factory hardening set",
    ):
        verify_promoted_factory_hardening(
            _evidence("ilaios.capability.core"),
            store=store,
        )


def test_receipt_from_another_capability_cannot_be_reused(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    capability_id = "ilaios.capability.research-data"
    receipts = list(_receipts(store, capability_id))
    foreign = record_hardening_receipt(
        store,
        capability_id="ilaios.capability.personal-operations",
        gate="recovery",
        source_revision=_SOURCE_REVISION,
        passed=True,
    )
    receipts[0] = foreign

    with pytest.raises(EnterpriseHardeningError, match="provenance binding mismatch"):
        verify_promoted_factory_hardening(
            _evidence(capability_id, receipts=tuple(receipts)),
            store=store,
        )


def test_receipts_are_bound_to_exact_source_revision(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    capability_id = "ilaios.capability.research-data"
    receipts = _receipts(store, capability_id)

    with pytest.raises(EnterpriseHardeningError, match="provenance binding mismatch"):
        verify_promoted_factory_hardening(
            _evidence(
                capability_id,
                source_revision=_OTHER_REVISION,
                receipts=receipts,
            ),
            store=store,
        )


def test_failed_gate_receipt_cannot_promote_factory(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    capability_id = "ilaios.capability.security-factory"
    receipts = _receipts(store, capability_id, failed_gate="cost_boundary")

    with pytest.raises(EnterpriseHardeningError, match="content binding mismatch"):
        verify_promoted_factory_hardening(
            _evidence(capability_id, receipts=receipts),
            store=store,
        )


def test_duplicate_receipt_gate_is_rejected(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    capability_id = "ilaios.capability.creative-document"
    receipts = _receipts(store, capability_id)

    with pytest.raises(EnterpriseHardeningError, match="duplicate enterprise"):
        verify_promoted_factory_hardening(
            _evidence(capability_id, receipts=(*receipts, receipts[0])),
            store=store,
        )


def test_unknown_gate_and_invalid_revision_are_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    with pytest.raises(EnterpriseHardeningError, match="unknown enterprise"):
        record_hardening_receipt(
            store,
            capability_id="ilaios.capability.research-data",
            gate="invented_gate",
            source_revision=_SOURCE_REVISION,
            passed=True,
        )
    with pytest.raises(EnterpriseHardeningError, match="40-hex source revision"):
        record_hardening_receipt(
            store,
            capability_id="ilaios.capability.research-data",
            gate="recovery",
            source_revision="master",
            passed=True,
        )


def test_artifact_tampering_invalidates_all_hardening_verification(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    store = EvidenceStore(root)
    evidence = _complete_evidence(store, "ilaios.capability.personal-operations")
    receipt = evidence.receipts[0]
    (root / "artifacts" / receipt.artifact_digest).write_bytes(b"tampered")

    with pytest.raises(EnterpriseHardeningError, match="integrity verification failed"):
        verify_promoted_factory_hardening(evidence, store=store)


def test_provenance_chain_tampering_invalidates_hardening_verification(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    store = EvidenceStore(root)
    evidence = _complete_evidence(store, "ilaios.capability.personal-operations")
    with sqlite3.connect(root / "provenance.sqlite3") as connection:
        connection.execute(
            "UPDATE provenance SET previous_hash = ? WHERE sequence = 2",
            ("f" * 64,),
        )

    with pytest.raises(EnterpriseHardeningError, match="integrity verification failed"):
        verify_promoted_factory_hardening(evidence, store=store)
