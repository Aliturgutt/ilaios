from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest

from services.reference_assets import (
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)
from src.video_automation.continuity_contracts import (
    BRAND_THRESHOLDS_V1,
    CHARACTER_THRESHOLDS_V1,
    BrandAssetSpec,
    BrandShotBinding,
    BrandVariant,
    CharacterSpec,
    ContinuityContractError,
    ContinuityEvidence,
    ContinuityRepair,
    ContinuityVerdict,
    ProviderContinuityCapabilities,
    ShotContinuityBinding,
    VideoContinuityContractBinder,
    validate_brand_continuity,
    validate_character_continuity,
)


def _record(asset_id: str, role: ReferenceAssetRole, digest: str) -> ReferenceAssetRecord:
    return ReferenceAssetRecord(
        asset_id=asset_id,
        principal_id="user-1",
        tenant_id="tenant-1",
        sha256=digest,
        mime_type="image/png",
        original_filename=f"{asset_id}.png",
        width=100,
        height=100,
        size_bytes=100,
        role=role,
        instruction=None,
        created_at=datetime.now(timezone.utc),
    )


class _Store:
    def __init__(self, records: tuple[ReferenceAssetRecord, ...]) -> None:
        self.records = {record.asset_id: record for record in records}
        self.job_assets = tuple(records)

    def for_request(self, request_id: str) -> tuple[ReferenceAssetRecord, ...]:
        if request_id != "job-1":
            return ()
        return self.job_assets

    def get_owned(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> ReferenceAssetRecord:
        record = self.records[asset_id]
        if record.principal_id != principal_id or record.tenant_id != tenant_id:
            raise ValueError("ownership mismatch")
        return record


def _binder(*records: ReferenceAssetRecord) -> VideoContinuityContractBinder:
    return VideoContinuityContractBinder(cast(ReferenceAssetStore, _Store(tuple(records))))


def _character(character_id: str, reference: str, *, job_id: str = "job-1") -> CharacterSpec:
    return CharacterSpec(
        character_id=character_id,
        tenant_id="tenant-1",
        job_id=job_id,
        revision=1,
        canonical_reference_asset_ids=(reference,),
        face_appearance="consistent face",
        wardrobe_costume=("charcoal jacket",),
        accessories_props=("watch",),
        provider_native_reference_handles=(f"native-{character_id}",),
    )


def _brand(source_hash: str) -> BrandAssetSpec:
    return BrandAssetSpec(
        brand_asset_id="brand-1",
        tenant_id="tenant-1",
        job_id="job-1",
        source_reference_asset_id="ref-logo",
        source_sha256=source_hash,
        revision=1,
        original_format="image/png",
        original_filename="logo.png",
        variants=(
            BrandVariant(
                variant_id="primary",
                reference_asset_id="ref-logo-variant",
                name="Primary",
                canonical_color_tokens=("#00C2D1",),
                text_wordmark_present=True,
                transparent_background_required=True,
            ),
        ),
        aspect_ratio=1.0,
    )


def _caps(*, subject: bool = True, brand: bool = True) -> ProviderContinuityCapabilities:
    return ProviderContinuityCapabilities(
        provider_id="provider-1",
        supports_subject_references=subject,
        supports_brand_references=brand,
    )


def test_same_character_across_shots_reuses_exact_reference_lineage() -> None:
    subject = _record("ref-subject-a", ReferenceAssetRole.SUBJECT, "a" * 64)
    binder = _binder(subject)
    character = _character("character-a", subject.asset_id)

    first = binder.plan_shot(
        binding=ShotContinuityBinding("job-1", "scene-1", "shot-1", ("character-a",)),
        characters=(character,),
        brands=(),
        principal_id="user-1",
        tenant_id="tenant-1",
        capabilities=_caps(),
    )
    second = binder.plan_shot(
        binding=ShotContinuityBinding("job-1", "scene-2", "shot-2", ("character-a",)),
        characters=(character,),
        brands=(),
        principal_id="user-1",
        tenant_id="tenant-1",
        capabilities=_caps(),
    )

    assert first.character_reference_asset_ids == ("ref-subject-a",)
    assert second.character_reference_asset_ids == first.character_reference_asset_ids
    assert second.character_native_handles == first.character_native_handles


def test_multi_character_keeps_reference_sets_separate_and_ordered() -> None:
    first = _record("ref-subject-a", ReferenceAssetRole.SUBJECT, "a" * 64)
    second = _record("ref-subject-b", ReferenceAssetRole.SUBJECT, "b" * 64)
    binder = _binder(first, second)
    plan = binder.plan_shot(
        binding=ShotContinuityBinding(
            "job-1", "scene-1", "shot-1", ("character-a", "character-b")
        ),
        characters=(
            _character("character-a", first.asset_id),
            _character("character-b", second.asset_id),
        ),
        brands=(),
        principal_id="user-1",
        tenant_id="tenant-1",
        capabilities=_caps(),
    )
    assert plan.character_reference_asset_ids == ("ref-subject-a", "ref-subject-b")


def test_cross_job_character_substitution_is_denied() -> None:
    subject = _record("ref-subject-a", ReferenceAssetRole.SUBJECT, "a" * 64)
    binder = _binder(subject)
    with pytest.raises(ContinuityContractError, match="cross-tenant or cross-job"):
        binder.plan_shot(
            binding=ShotContinuityBinding("job-1", "scene-1", "shot-1", ("character-a",)),
            characters=(_character("character-a", subject.asset_id, job_id="job-other"),),
            brands=(),
            principal_id="user-1",
            tenant_id="tenant-1",
            capabilities=_caps(),
        )


def test_unbound_reference_substitution_is_denied() -> None:
    bound = _record("ref-subject-a", ReferenceAssetRole.SUBJECT, "a" * 64)
    other = _record("ref-subject-b", ReferenceAssetRole.SUBJECT, "b" * 64)
    store = _Store((bound, other))
    store.job_assets = (bound,)
    binder = VideoContinuityContractBinder(cast(ReferenceAssetStore, store))
    with pytest.raises(ContinuityContractError, match="cross-job or unbound"):
        binder.plan_shot(
            binding=ShotContinuityBinding("job-1", "scene-1", "shot-1", ("character-b",)),
            characters=(_character("character-b", other.asset_id),),
            brands=(),
            principal_id="user-1",
            tenant_id="tenant-1",
            capabilities=_caps(),
        )


def test_strict_character_blocks_unsupported_provider() -> None:
    subject = _record("ref-subject-a", ReferenceAssetRole.SUBJECT, "a" * 64)
    binder = _binder(subject)
    with pytest.raises(ContinuityContractError, match="strict character references"):
        binder.plan_shot(
            binding=ShotContinuityBinding("job-1", "scene-1", "shot-1", ("character-a",)),
            characters=(_character("character-a", subject.asset_id),),
            brands=(),
            principal_id="user-1",
            tenant_id="tenant-1",
            capabilities=_caps(subject=False),
        )


def test_brand_defaults_to_deterministic_exact_logo_composition() -> None:
    source_hash = "c" * 64
    source = _record("ref-logo", ReferenceAssetRole.LOGO, source_hash)
    variant = _record("ref-logo-variant", ReferenceAssetRole.LOGO, "d" * 64)
    binder = _binder(source, variant)
    plan = binder.plan_shot(
        binding=ShotContinuityBinding(
            "job-1",
            "scene-1",
            "shot-1",
            (),
            (BrandShotBinding("brand-1", "primary", "overlay"),),
        ),
        characters=(),
        brands=(_brand(source_hash),),
        principal_id="user-1",
        tenant_id="tenant-1",
        capabilities=_caps(brand=False),
    )
    assert plan.deterministic_brand_asset_ids == ("brand-1",)
    assert plan.brand_reference_asset_ids == ()


def test_provider_conditioned_brand_receives_exact_variant_reference() -> None:
    source_hash = "c" * 64
    source = _record("ref-logo", ReferenceAssetRole.LOGO, source_hash)
    variant = _record("ref-logo-variant", ReferenceAssetRole.LOGO, "d" * 64)
    binder = _binder(source, variant)
    plan = binder.plan_shot(
        binding=ShotContinuityBinding(
            "job-1",
            "scene-1",
            "shot-1",
            (),
            (
                BrandShotBinding(
                    "brand-1",
                    "primary",
                    "product-surface",
                    generative_integration_required=True,
                ),
            ),
        ),
        characters=(),
        brands=(_brand(source_hash),),
        principal_id="user-1",
        tenant_id="tenant-1",
        capabilities=_caps(),
    )
    assert plan.brand_reference_asset_ids == ("ref-logo-variant",)
    assert plan.deterministic_brand_asset_ids == ()


def test_strict_generative_brand_blocks_unsupported_provider() -> None:
    source_hash = "c" * 64
    source = _record("ref-logo", ReferenceAssetRole.LOGO, source_hash)
    variant = _record("ref-logo-variant", ReferenceAssetRole.LOGO, "d" * 64)
    binder = _binder(source, variant)
    with pytest.raises(ContinuityContractError, match="strict brand reference"):
        binder.plan_shot(
            binding=ShotContinuityBinding(
                "job-1",
                "scene-1",
                "shot-1",
                (),
                (
                    BrandShotBinding(
                        "brand-1",
                        "primary",
                        "product-surface",
                        generative_integration_required=True,
                    ),
                ),
            ),
            characters=(),
            brands=(_brand(source_hash),),
            principal_id="user-1",
            tenant_id="tenant-1",
            capabilities=_caps(brand=False),
        )


def test_character_drift_returns_dimension_failures_and_same_lineage_repair() -> None:
    scores = {name: 1.0 for name in CHARACTER_THRESHOLDS_V1}
    scores["identity_face"] = 0.4
    scores["wardrobe_costume"] = 0.5
    result = validate_character_continuity(
        generated_asset=b"video-character",
        dimension_scores=scores,
    )
    assert result.verdict is ContinuityVerdict.FAIL
    assert result.failed_dimensions == ("identity_face", "wardrobe_costume")
    assert result.repair is ContinuityRepair.REGENERATE_SAME_LINEAGE


def test_brand_drift_prefers_canonical_overlay_repair() -> None:
    scores = {name: 1.0 for name in BRAND_THRESHOLDS_V1}
    scores["wordmark_text"] = 0.2
    scores["color_fidelity"] = 0.4
    result = validate_brand_continuity(
        generated_asset=b"video-brand",
        dimension_scores=scores,
        deterministic_overlay_allowed=True,
    )
    assert result.verdict is ContinuityVerdict.FAIL
    assert result.failed_dimensions == ("wordmark_text", "color_fidelity")
    assert result.repair is ContinuityRepair.REPLACE_WITH_CANONICAL_OVERLAY


def test_validation_fails_closed_when_dimensions_are_missing() -> None:
    with pytest.raises(ContinuityContractError, match="dimensions must match"):
        validate_character_continuity(
            generated_asset=b"video",
            dimension_scores={"identity_face": 1.0},
        )


def test_accepted_evidence_binds_exact_generated_asset_hash() -> None:
    scores = {name: 1.0 for name in CHARACTER_THRESHOLDS_V1}
    result = validate_character_continuity(
        generated_asset=b"accepted-video",
        dimension_scores=scores,
    )
    evidence = ContinuityEvidence(
        job_id="job-1",
        scene_id="scene-1",
        shot_id="shot-1",
        subject_or_brand_id="character-a",
        reference_asset_ids=("ref-subject-a",),
        reference_hashes=("a" * 64,),
        provider_id="provider-1",
        provider_request_id="request-1",
        generated_asset_sha256=result.generated_asset_sha256,
        validation=result,
    )
    assert evidence.validation.verdict is ContinuityVerdict.PASS
    with pytest.raises(ContinuityContractError, match="validation asset hash"):
        ContinuityEvidence(
            job_id="job-1",
            scene_id="scene-1",
            shot_id="shot-1",
            subject_or_brand_id="character-a",
            reference_asset_ids=("ref-subject-a",),
            reference_hashes=("a" * 64,),
            provider_id="provider-1",
            provider_request_id="request-1",
            generated_asset_sha256="f" * 64,
            validation=result,
        )
