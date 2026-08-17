"""Non-Microsoft release readiness must never infer missing external proof."""

from __future__ import annotations

from dataclasses import replace

import pytest

from services.non_microsoft_release_readiness import (
    NonMicrosoftReleaseEvidence,
    NonMicrosoftReleaseState,
    ReleaseReadinessError,
    evaluate_non_microsoft_release,
)


_SOURCE_SHA = "a" * 40


def _repository_ready_evidence() -> NonMicrosoftReleaseEvidence:
    return NonMicrosoftReleaseEvidence(
        source_sha=_SOURCE_SHA,
        google_desktop_oidc_verified=True,
        desktop_windows_gate_verified=True,
        desktop_package_verified=True,
        web_factory_verified=True,
        software_factory_verified=True,
        repository_ci_verified=True,
        release_manifest_verified=True,
        sbom_verified=True,
        third_party_notices_verified=True,
        artifact_checksums_verified=True,
        commercial_access_verified=True,
        website_exact_sha_deployed=False,
        provider_production_proof_verified=False,
        merchant_checkout_verified=False,
    )


def test_repository_ready_without_external_proofs_is_not_production() -> None:
    readiness = evaluate_non_microsoft_release(_repository_ready_evidence())

    assert readiness.state is NonMicrosoftReleaseState.EXTERNAL_PROOF_PENDING
    assert readiness.production_ready is False
    assert readiness.blockers == (
        "WEBSITE_EXACT_SHA_DEPLOYMENT_NOT_PROVEN",
        "REAL_PROVIDER_PRODUCTION_PROOF_NOT_PROVEN",
        "MERCHANT_CHECKOUT_NOT_PROVEN",
    )


def test_microsoft_dependencies_are_explicitly_excluded() -> None:
    readiness = evaluate_non_microsoft_release(_repository_ready_evidence())

    assert readiness.excluded_external_dependencies == (
        "MICROSOFT_DESKTOP_OIDC_APPROVAL",
        "MICROSOFT_SIGNED_MSIX_PUBLISHER_IDENTITY",
        "MICROSOFT_PARTNER_CENTER_STORE_CERTIFICATION",
    )
    assert all("MICROSOFT" not in blocker for blocker in readiness.blockers)


def test_all_non_microsoft_evidence_promotes_to_production_ready() -> None:
    evidence = replace(
        _repository_ready_evidence(),
        website_exact_sha_deployed=True,
        provider_production_proof_verified=True,
        merchant_checkout_verified=True,
    )

    readiness = evaluate_non_microsoft_release(evidence)

    assert readiness.state is NonMicrosoftReleaseState.PRODUCTION_READY
    assert readiness.production_ready is True
    assert readiness.blockers == ()


def test_missing_repository_evidence_prevents_external_only_promotion() -> None:
    evidence = replace(
        _repository_ready_evidence(),
        repository_ci_verified=False,
        website_exact_sha_deployed=True,
        provider_production_proof_verified=True,
        merchant_checkout_verified=True,
    )

    readiness = evaluate_non_microsoft_release(evidence)

    assert readiness.state is NonMicrosoftReleaseState.REPOSITORY_INCOMPLETE
    assert readiness.blockers == ("REPOSITORY_CI_NOT_VERIFIED",)


def test_release_evidence_rejects_malformed_source_sha() -> None:
    with pytest.raises(ReleaseReadinessError, match="source_sha"):
        replace(_repository_ready_evidence(), source_sha="not-a-sha")
