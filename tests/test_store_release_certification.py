from __future__ import annotations

import pytest

from services.store_release_certification import (
    CertificationEvidence,
    PolicyRule,
    StoreCertificationError,
    StoreCertificationPermissionError,
    assert_submitted_binary_matches_certified,
    build_artifact_identity,
    build_credential_reference,
    build_policy_snapshot,
    build_submission_profile,
    evaluate_policy,
    policy_allows_release,
    policy_snapshot_is_stale,
    submit_or_publish_store_release,
    transition_release_state,
    validate_certification_evidence,
)


_SHA = "a" * 64
_SOURCE_SHA = "b" * 40


def _rule(*, key: str = "always", value: str = "true", evidence: tuple[str, ...] = ("receipt",)) -> PolicyRule:
    return PolicyRule(
        rule_id="TEST-001",
        store="google-play",
        policy_version="2026-08-19",
        territory="global",
        applicability_key=key,
        applicability_value=value,
        severity="BLOCK",
        validation_method="deterministic-test",
        required_evidence=evidence,
        official_source="official-source-id",
        last_verified="2026-08-19",
        autofix_allowed=False,
    )


def _profile() -> object:
    return build_submission_profile(
        app_id="com.ilaios.mobile",
        platform="android",
        store="google-play",
        territories=("TR",),
        auth_methods=("email",),
        account_creation=True,
        permissions=("camera",),
        tracking=False,
        monetization="free",
    )


def _evidence() -> CertificationEvidence:
    artifact = build_artifact_identity(
        source_sha=_SOURCE_SHA,
        build_id="build-42",
        binary_sha256=_SHA,
        version="1.0.0",
        build_number="42",
    )
    return CertificationEvidence(
        artifact=artifact,
        device_test_receipts=("device://receipt/1",),
        runtime_receipts=("runtime://receipt/1",),
        privacy_scan_sha256=_SHA,
        sdk_inventory_sha256=_SHA,
        permission_scan_sha256=_SHA,
        commerce_e2e_receipts=(),
        metadata_snapshot_sha256=_SHA,
        screenshot_sha256s=(_SHA,),
        policy_snapshot_sha256=_SHA,
        certification_result_sha256=_SHA,
    )


def test_submission_profile_is_content_addressed_and_store_platform_bounded() -> None:
    profile = build_submission_profile(
        app_id="com.ilaios.mobile",
        platform="android",
        store="google-play",
        territories=("TR", "DE"),
        auth_methods=("email",),
    )
    same = build_submission_profile(
        app_id="com.ilaios.mobile",
        platform="android",
        store="google-play",
        territories=("TR", "DE"),
        auth_methods=("email",),
    )
    assert profile.profile_sha256 == same.profile_sha256
    assert len(profile.profile_sha256) == 64

    with pytest.raises(StoreCertificationError, match="platform/store pairing"):
        build_submission_profile(
            app_id="com.ilaios.mobile",
            platform="android",
            store="apple-app-store",
            territories=("TR",),
        )


def test_submission_profile_rejects_duplicates_and_missing_territory() -> None:
    with pytest.raises(StoreCertificationError, match="at least one distribution territory"):
        build_submission_profile(
            app_id="com.ilaios.mobile", platform="android", store="google-play", territories=()
        )
    with pytest.raises(StoreCertificationError, match="duplicate"):
        build_submission_profile(
            app_id="com.ilaios.mobile",
            platform="android",
            store="google-play",
            territories=("TR", "TR"),
        )


def test_policy_snapshot_is_deterministic_and_rejects_cross_store_rules() -> None:
    rule = _rule()
    snapshot = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(rule,),
    )
    same = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(rule,),
    )
    assert snapshot.snapshot_sha256 == same.snapshot_sha256

    foreign = PolicyRule(
        rule_id="APPLE-001",
        store="apple-app-store",
        policy_version="2026-08-19",
        territory="global",
        applicability_key="always",
        applicability_value="true",
        severity="BLOCK",
        validation_method="deterministic-test",
        required_evidence=("receipt",),
        official_source="official-source-id",
        last_verified="2026-08-19",
        autofix_allowed=False,
    )
    with pytest.raises(StoreCertificationError, match="another store"):
        build_policy_snapshot(
            store="google-play",
            policy_version="2026-08-19",
            retrieved_at="2026-08-19T12:00:00Z",
            verified_at="2026-08-19T12:01:00Z",
            rules=(foreign,),
        )


def test_unknown_policy_applicability_fails_closed() -> None:
    profile = build_submission_profile(
        app_id="com.ilaios.mobile", platform="android", store="google-play", territories=("TR",)
    )
    snapshot = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(_rule(key="future-unknown-predicate"),),
    )
    evaluations = evaluate_policy(profile, snapshot)
    assert evaluations[0].outcome == "BLOCK"
    assert not policy_allows_release(evaluations)


def test_conditional_policy_can_be_not_applicable() -> None:
    profile = build_submission_profile(
        app_id="com.ilaios.mobile",
        platform="android",
        store="google-play",
        territories=("TR",),
        tracking=False,
    )
    snapshot = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(_rule(key="tracking", value="true"),),
    )
    evaluations = evaluate_policy(profile, snapshot)
    assert evaluations[0].outcome == "NOT_APPLICABLE"
    assert policy_allows_release(evaluations)


def test_blocking_rule_without_evidence_contract_fails_closed() -> None:
    profile = build_submission_profile(
        app_id="com.ilaios.mobile", platform="android", store="google-play", territories=("TR",)
    )
    snapshot = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(_rule(evidence=()),),
    )
    evaluations = evaluate_policy(profile, snapshot)
    assert evaluations[0].outcome == "BLOCK"


def test_policy_snapshot_staleness_is_content_identity_based() -> None:
    snapshot = build_policy_snapshot(
        store="google-play",
        policy_version="2026-08-19",
        retrieved_at="2026-08-19T12:00:00Z",
        verified_at="2026-08-19T12:01:00Z",
        rules=(_rule(),),
    )
    assert not policy_snapshot_is_stale(
        certified_snapshot_sha256=snapshot.snapshot_sha256, current_snapshot=snapshot
    )
    assert policy_snapshot_is_stale(certified_snapshot_sha256=_SHA, current_snapshot=snapshot)


def test_release_state_machine_rejects_maturity_skip() -> None:
    assert transition_release_state("DESIGNED", "SPECIFIED") == "SPECIFIED"
    with pytest.raises(StoreCertificationError, match="invalid release transition"):
        transition_release_state("DESIGNED", "STORE_READY")


def test_evidence_identity_invalidates_mismatched_submitted_binary() -> None:
    evidence = _evidence()
    validate_certification_evidence(evidence)
    assert_submitted_binary_matches_certified(certified=evidence, submitted_binary_sha256=_SHA)
    with pytest.raises(StoreCertificationError, match="does not match certified binary"):
        assert_submitted_binary_matches_certified(certified=evidence, submitted_binary_sha256="c" * 64)


def test_credential_boundary_is_opaque_and_scoped() -> None:
    reference = build_credential_reference(
        tenant_id="tenant-1", credential_id="cred-ref-1", scopes=("store.read",)
    )
    assert reference.tenant_id == "tenant-1"
    assert reference.credential_id == "cred-ref-1"
    assert reference.scopes == ("store.read",)
    with pytest.raises(StoreCertificationError, match="at least one scope"):
        build_credential_reference(tenant_id="tenant-1", credential_id="cred-ref-1", scopes=())


def test_store_submission_and_publication_are_not_authorized_here() -> None:
    with pytest.raises(StoreCertificationPermissionError, match="Approval Engine and Tool Gateway"):
        submit_or_publish_store_release()
