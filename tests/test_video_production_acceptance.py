from __future__ import annotations

from dataclasses import replace

import pytest

from src.video_automation.production_acceptance import (
    EndToEndProductionProof,
    LegalProvenanceProductionProof,
    OperationsSloProductionProof,
    PerceptualDomainProof,
    PerceptualQaProductionProof,
    ProviderProductionProof,
    PublicationProductionProof,
    RightsEvidence,
    VideoProductionAcceptanceError,
    VideoProductionEvidenceBundle,
    evaluate_video_production,
)

REVISION = "a" * 40
PRODUCT_ID = "finished-video-prod-001"
ARTIFACT_SHA = "b" * 64
PROMPT_SHA = "c" * 64
MANIFEST_SHA = "d" * 64
CRITERIA_SHA = "e" * 64
ASSET_INVENTORY_SHA = "f" * 64


def _provider(*, fallback_required: bool = True) -> ProviderProductionProof:
    return ProviderProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider_name="openrouter-video-primary",
        credential_reference="secret://video/openrouter/production",
        request_id="provider-request-001",
        external_job_id="external-job-001",
        generation_receipt_ref="evidence://provider/generation-001",
        artifact_receipt_ref="evidence://provider/artifact-001",
        succeeded=True,
        fallback_required=fallback_required,
        fallback_exercised=fallback_required,
        fallback_provider_name=(
            "volcengine-seedance-fallback" if fallback_required else None
        ),
        fallback_receipt_ref=(
            "evidence://provider/fallback-001" if fallback_required else None
        ),
    )


def _perceptual() -> PerceptualQaProductionProof:
    reviews = tuple(
        PerceptualDomainProof(
            domain=domain,
            review_id=f"review-{domain.lower()}-001",
            reviewer_id=f"independent-{domain.lower()}-reviewer",
            producer_id="video-producer-001",
            criteria_version="1.0",
            criteria_sha256=CRITERIA_SHA,
            evidence_ref=f"evidence://qa/{domain.lower()}-001",
            score=0.95,
            threshold=0.90,
            repair_attempts=1 if domain == "VISUAL" else 0,
            max_repair_attempts=2,
        )
        for domain in ("VISUAL", "AUDIO", "BRAND")
    )
    return PerceptualQaProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        producer_id="video-producer-001",
        reviews=reviews,
        sealed_evidence_ref="evidence://qa/sealed-001",
    )


def _publication() -> PublicationProductionProof:
    return PublicationProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        package_id="publish-package-001",
        platform="youtube",
        account_id="youtube-test-account-001",
        oauth_authorization_ref="oauth://youtube/test-account-001",
        platform_post_id="youtube-post-001",
        published_url="https://www.youtube.com/watch?v=production-proof-001",
        publication_receipt_ref="evidence://publish/receipt-001",
        verification_receipt_ref="evidence://publish/verify-001",
        duplicate_prevention_ref="evidence://publish/idempotency-001",
        retry_reconciliation_ref="evidence://publish/reconcile-001",
        ledger_state="PUBLISHED",
    )


def _operations() -> OperationsSloProductionProof:
    return OperationsSloProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        window_start="2026-08-15T09:00:00+00:00",
        window_end="2026-08-15T10:00:00+00:00",
        sample_count=20,
        cost_usd=0.80,
        cost_budget_usd=1.00,
        p95_latency_ms=48_000.0,
        p95_latency_target_ms=60_000.0,
        availability_ratio=1.0,
        availability_target_ratio=0.99,
        quality_pass_ratio=0.95,
        quality_target_ratio=0.90,
        telemetry_evidence_ref="evidence://ops/telemetry-001",
        alert_evidence_ref="evidence://ops/alerts-001",
        slo_evidence_ref="evidence://ops/slo-001",
    )


def _legal() -> LegalProvenanceProductionProof:
    return LegalProvenanceProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        expected_asset_ids=("generated-shot-001", "voice-001"),
        asset_inventory_ref="evidence://assets/inventory-001",
        asset_inventory_sha256=ASSET_INVENTORY_SHA,
        rights=(
            RightsEvidence(
                asset_id="generated-shot-001",
                asset_role="video-generation-output",
                source_ref="provider://openrouter/job/external-job-001",
                provenance_ref="evidence://provenance/generated-shot-001",
                license_or_terms_ref="terms://provider/commercial-output-v1",
                consent_ref=None,
                commercial_use_allowed=True,
            ),
            RightsEvidence(
                asset_id="voice-001",
                asset_role="narration",
                source_ref="library://voice/approved-001",
                provenance_ref="evidence://provenance/voice-001",
                license_or_terms_ref="license://voice/commercial-001",
                consent_ref="consent://voice/001",
                commercial_use_allowed=True,
            ),
        ),
        complete_asset_inventory=True,
        model_output_terms_ref="terms://provider/commercial-output-v1",
        rights_manifest_ref="evidence://rights/manifest-001",
        legal_release_ref="evidence://rights/release-001",
    )


def _e2e() -> EndToEndProductionProof:
    return EndToEndProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        authenticated_subject_ref="identity://test-user-001",
        prompt_sha256=PROMPT_SHA,
        run_id="video-production-run-001",
        provider_request_id="provider-request-001",
        delivery_receipt_ref="evidence://delivery/001",
        publication_receipt_ref="evidence://publish/receipt-001",
        immutable_evidence_manifest_sha256=MANIFEST_SHA,
        stages=(
            "AUTHENTICATED",
            "PROMPT_ACCEPTED",
            "PLANNED",
            "GENERATED",
            "EDITED",
            "QA_EVALUATED",
            "REPAIR_RESOLVED",
            "FINISHED_PRODUCT_CERTIFIED",
            "DELIVERED",
            "PUBLISHED",
            "EVIDENCE_SEALED",
        ),
        succeeded=True,
    )


def _complete_bundle() -> VideoProductionEvidenceBundle:
    return VideoProductionEvidenceBundle(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider=_provider(),
        perceptual_qa=_perceptual(),
        publication=_publication(),
        operations=_operations(),
        legal_provenance=_legal(),
        end_to_end=_e2e(),
    )


def test_missing_external_evidence_remains_blocked() -> None:
    decision = evaluate_video_production(
        VideoProductionEvidenceBundle(
            revision_sha=REVISION,
            product_id=PRODUCT_ID,
            artifact_sha256=ARTIFACT_SHA,
        )
    )

    assert decision.state == "BLOCKED"
    assert decision.production is False
    assert len(decision.blockers) == 6
    assert "missing credentialed production-provider proof" in decision.blockers
    assert len(decision.decision_sha256) == 64


def test_complete_exact_artifact_evidence_promotes_to_production() -> None:
    decision = evaluate_video_production(_complete_bundle())

    assert decision.state == "PRODUCTION"
    assert decision.production is True
    assert decision.blockers == ()
    assert decision.revision_sha == REVISION
    assert decision.product_id == PRODUCT_ID
    assert decision.artifact_sha256 == ARTIFACT_SHA


def test_required_fallback_must_be_real_and_receipted() -> None:
    provider = ProviderProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider_name="openrouter-video-primary",
        credential_reference="secret://video/openrouter/production",
        request_id="provider-request-001",
        external_job_id="external-job-001",
        generation_receipt_ref="evidence://provider/generation-001",
        artifact_receipt_ref="evidence://provider/artifact-001",
        succeeded=True,
        fallback_required=True,
        fallback_exercised=False,
    )
    bundle = VideoProductionEvidenceBundle(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider=provider,
        perceptual_qa=_perceptual(),
        publication=_publication(),
        operations=_operations(),
        legal_provenance=_legal(),
        end_to_end=_e2e(),
    )

    decision = evaluate_video_production(bundle)

    assert decision.state == "BLOCKED"
    assert "required real provider fallback proof is missing" in decision.blockers


def test_mismatched_artifact_identity_cannot_be_promoted() -> None:
    provider = ProviderProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256="f" * 64,
        provider_name="openrouter-video-primary",
        credential_reference="secret://video/openrouter/production",
        request_id="provider-request-001",
        external_job_id="external-job-001",
        generation_receipt_ref="evidence://provider/generation-001",
        artifact_receipt_ref="evidence://provider/artifact-001",
        succeeded=True,
        fallback_required=False,
        fallback_exercised=False,
    )
    bundle = VideoProductionEvidenceBundle(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider=provider,
        perceptual_qa=_perceptual(),
        publication=_publication(),
        operations=_operations(),
        legal_provenance=_legal(),
        end_to_end=_e2e(),
    )

    decision = evaluate_video_production(bundle)

    assert decision.state == "BLOCKED"
    assert (
        "provider proof identity does not match exact production artifact"
        in decision.blockers
    )


def test_perceptual_reviewer_must_be_independent() -> None:
    with pytest.raises(
        VideoProductionAcceptanceError,
        match="reviewer must be independent",
    ):
        PerceptualDomainProof(
            domain="VISUAL",
            review_id="review-visual-001",
            reviewer_id="same-actor",
            producer_id="same-actor",
            criteria_version="1.0",
            criteria_sha256=CRITERIA_SHA,
            evidence_ref="evidence://qa/visual-001",
            score=1.0,
            threshold=0.9,
            repair_attempts=0,
            max_repair_attempts=1,
        )


def test_operations_outside_slo_remain_blocked() -> None:
    operations = OperationsSloProductionProof(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        window_start="2026-08-15T09:00:00+00:00",
        window_end="2026-08-15T10:00:00+00:00",
        sample_count=10,
        cost_usd=1.20,
        cost_budget_usd=1.00,
        p95_latency_ms=61_000.0,
        p95_latency_target_ms=60_000.0,
        availability_ratio=0.98,
        availability_target_ratio=0.99,
        quality_pass_ratio=0.89,
        quality_target_ratio=0.90,
        telemetry_evidence_ref="evidence://ops/telemetry-002",
        alert_evidence_ref="evidence://ops/alerts-002",
        slo_evidence_ref="evidence://ops/slo-002",
    )
    bundle = VideoProductionEvidenceBundle(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider=_provider(),
        perceptual_qa=_perceptual(),
        publication=_publication(),
        operations=operations,
        legal_provenance=_legal(),
        end_to_end=_e2e(),
    )

    decision = evaluate_video_production(bundle)

    assert decision.state == "BLOCKED"
    assert (
        "production operations SLO evidence is outside accepted thresholds"
        in decision.blockers
    )


def test_single_good_slo_sample_cannot_promote_production() -> None:
    operations = replace(_operations(), sample_count=1)
    bundle = replace(_complete_bundle(), operations=operations)

    decision = evaluate_video_production(bundle)

    assert decision.state == "BLOCKED"
    assert (
        "production operations SLO evidence is outside accepted thresholds"
        in decision.blockers
    )


def test_legal_inventory_must_exactly_match_rights_evidence() -> None:
    legal = replace(
        _legal(),
        expected_asset_ids=("generated-shot-001", "voice-001", "music-001"),
    )
    bundle = replace(_complete_bundle(), legal_provenance=legal)

    decision = evaluate_video_production(bundle)

    assert decision.state == "BLOCKED"
    assert (
        "legal provenance inventory is incomplete or not commercially cleared"
        in decision.blockers
    )


def test_legal_inventory_reference_must_be_cryptographically_bound() -> None:
    with pytest.raises(
        VideoProductionAcceptanceError,
        match="asset_inventory_sha256 must be lowercase SHA-256",
    ):
        replace(_legal(), asset_inventory_sha256="not-a-sha")
