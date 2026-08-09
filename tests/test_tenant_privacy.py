"""Bounded proofs for DATA.I04."""

from datetime import datetime, timedelta, timezone

import pytest

from services.privacy import (
    DataRecord,
    DataState,
    LegalHold,
    PrivacyError,
    RegulatoryProfile,
    TenantDataPolicy,
    TenantDataStore,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _store(*, blocked: frozenset[str] = frozenset()) -> TenantDataStore:
    store = TenantDataStore()
    store.register_policy(
        TenantDataPolicy(
            "tenant-a",
            frozenset({"eu"}),
            timedelta(days=30),
            frozenset({"support"}),
            frozenset({"email"}),
            blocked,
            RegulatoryProfile(
                "modular-profile", frozenset({"eu"}), frozenset({"restricted"})
            ),
        )
    )
    return store


def _record(classifications: frozenset[str] = frozenset()) -> DataRecord:
    return DataRecord(
        "record-1",
        "tenant-a",
        "eu",
        "support",
        (("email", "a@example.test"),),
        classifications,
        NOW,
    )


def test_residency_purpose_minimization_and_cross_tenant_fail_closed() -> None:
    store = _store()
    store.create(_record(), "human-1")
    assert store.read("record-1", "tenant-a", "human-1", NOW).tenant_id == "tenant-a"
    with pytest.raises(PrivacyError, match="tenant"):
        store.read("record-1", "tenant-b", "human-1", NOW)
    with pytest.raises(PrivacyError, match="residency"):
        store.create(
            DataRecord("r2", "tenant-a", "us", "support", (), frozenset(), NOW),
            "human-1",
        )
    with pytest.raises(PrivacyError, match="minimization"):
        store.create(
            DataRecord(
                "r3", "tenant-a", "eu", "support", (("extra", "x"),), frozenset(), NOW
            ),
            "human-1",
        )


def test_dlp_and_modular_profile_block_export_without_certification_claim() -> None:
    store = _store(blocked=frozenset({"secret"}))
    store.create(_record(frozenset({"secret"})), "human-1")
    with pytest.raises(PrivacyError, match="DLP"):
        store.export("record-1", "tenant-a", "human-1", NOW)


def test_legal_hold_blocks_then_allows_audited_deletion_lifecycle() -> None:
    store = _store()
    store.create(_record(), "human-1")
    hold = LegalHold("hold-1", "tenant-a", "record-1", "litigation", "legal-1")
    store.place_hold(hold, "legal-1", NOW)
    with pytest.raises(PrivacyError, match="legal hold"):
        store.request_deletion("record-1", "tenant-a", "human-1", NOW)
    store.release_hold("hold-1", "legal-1", NOW)
    pending = store.request_deletion("record-1", "tenant-a", "human-1", NOW)
    assert pending.state is DataState.DELETION_PENDING
    deleted = store.execute_deletion("record-1", "tenant-a", "worker-1", NOW)
    assert deleted.state is DataState.DELETED and deleted.fields == ()
    assert [event.operation for event in store.events()][-4:] == [
        "legal_hold",
        "release_hold",
        "deletion_request",
        "delete",
    ]
