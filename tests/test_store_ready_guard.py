from __future__ import annotations

from dataclasses import replace

import pytest

from services.store_ready_guard import promote_store_ready
from services.store_release_certification import (
    CertificationEvidence,
    PolicyRule,
    StoreCertificationError,
    build_artifact_identity,
    build_policy_snapshot,
    build_submission_profile,
)

_SHA256 = "a" * 64
_SOURCE_SHA = "b" * 40


def _profile(*, monetization: str = "free"):
    return build_submission_profile(
        app_id="com.ilaios.mobile",
        platform="android",
        store="google-play",
        territories=("TR",),
        auth_methods=("email",),
        account_creation=True,
        permissions=("camera",),
        monetization=monetization,
    )


def _snapshot(*, blocking: bool = False):
    rule = PolicyRule(
        rule_id="PLAY-READY-001",
        store="google-play",
        policy_version="2026-08-28",
        territory="global",
        applicability_key="always",
        applicability_value="true",
        severity="BLOCK",
        validation_method="receipt",
        required_evidence=() if blocking else ("runtime-receipt",),
        official_source="google-play-policy",
        last_verified="2026-08-28",
        autofix_allowed=False,
    )
    return build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-28",
        retrieved_at="2026-08-28T10:00:00Z",
        verified_at="2026-08-28T10:01:00Z",
        rules=(rule,),
    )


def _evidence(snapshot_sha: str) -> CertificationEvidence:
    return CertificationEvidence(
        artifact=build_artifact_identity(
            source_sha=_SOURCE_SHA,
            build_id="build-100",
            binary_sha256=_SHA256,
            version="1.0.0",
            build_number="100",
        ),
        device_test_receipts=("device://receipt/1",),
        runtime_receipts=("runtime://receipt/1",),
        privacy_scan_sha256=_SHA256,
        sdk_inventory_sha256=_SHA256,
        permission_scan_sha256=_SHA256,
        commerce_e2e_receipts=(),
        metadata_snapshot_sha256=_SHA256,
        screenshot_sha256s=(_SHA256,),
        policy_snapshot_sha256=snapshot_sha,
        certification_result_sha256=_SHA256,
    )


def test_store_ready_requires_bound_policy_and_external_evidence_presence() -> None:
    profile = _profile()
    snapshot = _snapshot()
    evidence = _evidence(snapshot.snapshot_sha256)

    assert (
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=profile,
            policy_snapshot=snapshot,
            evidence=evidence,
        )
        == "STORE_READY"
    )

    with pytest.raises(StoreCertificationError, match="stale policy snapshot"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=profile,
            policy_snapshot=snapshot,
            evidence=replace(evidence, policy_snapshot_sha256="c" * 64),
        )

    with pytest.raises(StoreCertificationError, match="device test evidence"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=profile,
            policy_snapshot=snapshot,
            evidence=replace(evidence, device_test_receipts=()),
        )

    with pytest.raises(StoreCertificationError, match="runtime/stability evidence"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=profile,
            policy_snapshot=snapshot,
            evidence=replace(evidence, runtime_receipts=()),
        )

    with pytest.raises(StoreCertificationError, match="listing screenshot evidence"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=profile,
            policy_snapshot=snapshot,
            evidence=replace(evidence, screenshot_sha256s=()),
        )


def test_store_ready_fails_closed_on_policy_and_commerce() -> None:
    blocked_snapshot = _snapshot(blocking=True)
    blocked_evidence = _evidence(blocked_snapshot.snapshot_sha256)
    with pytest.raises(StoreCertificationError, match="policy evaluation blocks"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=_profile(),
            policy_snapshot=blocked_snapshot,
            evidence=blocked_evidence,
        )

    paid_snapshot = _snapshot()
    paid_evidence = _evidence(paid_snapshot.snapshot_sha256)
    with pytest.raises(StoreCertificationError, match="commerce E2E evidence"):
        promote_store_ready(
            current="STORE_CERTIFYING",
            profile=_profile(monetization="subscription"),
            policy_snapshot=paid_snapshot,
            evidence=paid_evidence,
        )

    assert (
        promote_store_ready(
            current="RE_CERTIFYING",
            profile=_profile(monetization="subscription"),
            policy_snapshot=paid_snapshot,
            evidence=replace(paid_evidence, commerce_e2e_receipts=("commerce://receipt/1",)),
        )
        == "STORE_READY"
    )


def test_store_ready_rejects_non_certifying_state() -> None:
    snapshot = _snapshot()
    with pytest.raises(StoreCertificationError, match="certifying state"):
        promote_store_ready(
            current="TESTED",
            profile=_profile(),
            policy_snapshot=snapshot,
            evidence=_evidence(snapshot.snapshot_sha256),
        )
