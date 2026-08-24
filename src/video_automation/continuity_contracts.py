"""Canonical character and brand continuity contracts for Video Factory.

This module is an additive contract/binding layer over the existing Video Factory,
ReferenceAssetStore, native-reference provider path and deterministic logo-lock
composition.  It does not identify real people, create a second asset store,
provider router, validation authority or video engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Callable, Mapping, TypeVar

from services.reference_assets import (
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)


class ContinuityContractError(ValueError):
    """Raised when continuity authority or provenance is ambiguous."""


class ContinuityVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNSUPPORTED = "UNSUPPORTED"


class BrandRenderMode(str, Enum):
    DETERMINISTIC_OVERLAY = "deterministic_overlay"
    PROVIDER_CONDITIONED = "provider_conditioned"


class ContinuityRepair(str, Enum):
    NONE = "none"
    REGENERATE_SAME_LINEAGE = "regenerate_same_lineage"
    REPLACE_WITH_CANONICAL_OVERLAY = "replace_with_canonical_overlay"
    BLOCK_UNSUPPORTED = "block_unsupported"


CHARACTER_THRESHOLDS_V1: Mapping[str, float] = MappingProxyType(
    {
        "identity_face": 0.88,
        "hair_facial_hair": 0.84,
        "wardrobe_costume": 0.84,
        "body_proportion": 0.80,
        "accessories_props": 0.82,
        "color_markers": 0.84,
        "cross_shot": 0.86,
    }
)

BRAND_THRESHOLDS_V1: Mapping[str, float] = MappingProxyType(
    {
        "geometry_silhouette": 0.96,
        "wordmark_text": 0.99,
        "proportion": 0.98,
        "color_fidelity": 0.95,
        "variant": 1.0,
        "orientation": 0.98,
        "background_transparency": 0.94,
        "deformation_crop": 0.98,
        "duplicate_extra": 1.0,
        "placement_safe_area": 0.94,
        "cross_brand": 1.0,
    }
)


@dataclass(frozen=True, slots=True)
class CharacterSpec:
    character_id: str
    tenant_id: str
    job_id: str
    revision: int
    canonical_reference_asset_ids: tuple[str, ...]
    face_appearance: str | None = None
    age_range: str | None = None
    hair_facial_hair: str | None = None
    body_build_proportion: str | None = None
    wardrobe_costume: tuple[str, ...] = ()
    color_palette: tuple[str, ...] = ()
    accessories_props: tuple[str, ...] = ()
    voice_persona_id: str | None = None
    provider_native_reference_handles: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    provenance: str = "user-approved"
    strict_identity: bool = True

    def __post_init__(self) -> None:
        _id("character_id", self.character_id)
        _id("tenant_id", self.tenant_id)
        _id("job_id", self.job_id)
        if self.revision < 1:
            raise ContinuityContractError("character revision must be >= 1")
        _unique_ids("canonical_reference_asset_ids", self.canonical_reference_asset_ids)
        if self.strict_identity and not self.canonical_reference_asset_ids:
            raise ContinuityContractError("strict character continuity requires references")
        _texts("wardrobe_costume", self.wardrobe_costume)
        _texts("color_palette", self.color_palette)
        _texts("accessories_props", self.accessories_props)
        _texts("provider_native_reference_handles", self.provider_native_reference_handles)
        _texts("negative_constraints", self.negative_constraints)
        _optional_text("face_appearance", self.face_appearance)
        _optional_text("age_range", self.age_range)
        _optional_text("hair_facial_hair", self.hair_facial_hair)
        _optional_text("body_build_proportion", self.body_build_proportion)
        _optional_text("voice_persona_id", self.voice_persona_id)
        _text("provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class BrandVariant:
    variant_id: str
    reference_asset_id: str
    name: str
    canonical_color_tokens: tuple[str, ...] = ()
    clear_space_ratio: float | None = None
    text_wordmark_present: bool = False
    transparent_background_required: bool = False

    def __post_init__(self) -> None:
        _id("variant_id", self.variant_id)
        _id("reference_asset_id", self.reference_asset_id)
        _text("name", self.name)
        _texts("canonical_color_tokens", self.canonical_color_tokens)
        if self.clear_space_ratio is not None and self.clear_space_ratio < 0:
            raise ContinuityContractError("clear_space_ratio must not be negative")


@dataclass(frozen=True, slots=True)
class BrandAssetSpec:
    brand_asset_id: str
    tenant_id: str
    job_id: str
    source_reference_asset_id: str
    source_sha256: str
    revision: int
    original_format: str
    original_filename: str
    variants: tuple[BrandVariant, ...]
    aspect_ratio: float
    provenance: str = "authorized-user-upload"

    def __post_init__(self) -> None:
        _id("brand_asset_id", self.brand_asset_id)
        _id("tenant_id", self.tenant_id)
        _id("job_id", self.job_id)
        _id("source_reference_asset_id", self.source_reference_asset_id)
        _sha("source_sha256", self.source_sha256)
        if self.revision < 1:
            raise ContinuityContractError("brand revision must be >= 1")
        _text("original_format", self.original_format)
        _text("original_filename", self.original_filename)
        _text("provenance", self.provenance)
        if self.aspect_ratio <= 0:
            raise ContinuityContractError("brand aspect_ratio must be positive")
        variant_ids = [variant.variant_id for variant in self.variants]
        if len(variant_ids) != len(set(variant_ids)):
            raise ContinuityContractError("brand variant ids must be unique")
        reference_ids = [variant.reference_asset_id for variant in self.variants]
        if len(reference_ids) != len(set(reference_ids)):
            raise ContinuityContractError("brand variant references must be unique")


@dataclass(frozen=True, slots=True)
class BrandShotBinding:
    brand_asset_id: str
    variant_id: str
    placement_intent: str
    strict_fidelity: bool = True
    generative_integration_required: bool = False

    def __post_init__(self) -> None:
        _id("brand_asset_id", self.brand_asset_id)
        _id("variant_id", self.variant_id)
        if self.placement_intent not in {
            "overlay",
            "environment",
            "object",
            "watermark",
            "end-card",
            "lower-third",
            "product-surface",
        }:
            raise ContinuityContractError("unsupported brand placement intent")


@dataclass(frozen=True, slots=True)
class ShotContinuityBinding:
    job_id: str
    scene_id: str
    shot_id: str
    character_ids: tuple[str, ...] = ()
    brand_bindings: tuple[BrandShotBinding, ...] = ()

    def __post_init__(self) -> None:
        _id("job_id", self.job_id)
        _id("scene_id", self.scene_id)
        _id("shot_id", self.shot_id)
        _unique_ids("character_ids", self.character_ids)
        brands = [binding.brand_asset_id for binding in self.brand_bindings]
        if len(brands) != len(set(brands)):
            raise ContinuityContractError("one shot cannot bind the same brand twice")


@dataclass(frozen=True, slots=True)
class ProviderContinuityCapabilities:
    provider_id: str
    supports_subject_references: bool
    supports_brand_references: bool

    def __post_init__(self) -> None:
        _id("provider_id", self.provider_id)


@dataclass(frozen=True, slots=True)
class ProviderConditioningPlan:
    provider_id: str
    character_reference_asset_ids: tuple[str, ...]
    character_native_handles: tuple[str, ...]
    brand_reference_asset_ids: tuple[str, ...]
    deterministic_brand_asset_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DimensionResult:
    name: str
    score: float
    threshold: float
    passed: bool


@dataclass(frozen=True, slots=True)
class ContinuityValidationResult:
    verdict: ContinuityVerdict
    dimensions: tuple[DimensionResult, ...]
    generated_asset_sha256: str
    failed_dimensions: tuple[str, ...]
    repair: ContinuityRepair


@dataclass(frozen=True, slots=True)
class ContinuityEvidence:
    job_id: str
    scene_id: str
    shot_id: str
    subject_or_brand_id: str
    reference_asset_ids: tuple[str, ...]
    reference_hashes: tuple[str, ...]
    provider_id: str
    provider_request_id: str
    generated_asset_sha256: str
    validation: ContinuityValidationResult
    retry_parent_asset_sha256: str | None = None

    def __post_init__(self) -> None:
        _id("job_id", self.job_id)
        _id("scene_id", self.scene_id)
        _id("shot_id", self.shot_id)
        _id("subject_or_brand_id", self.subject_or_brand_id)
        _unique_ids("reference_asset_ids", self.reference_asset_ids)
        for digest in self.reference_hashes:
            _sha("reference_hash", digest)
        _id("provider_id", self.provider_id)
        _id("provider_request_id", self.provider_request_id)
        _sha("generated_asset_sha256", self.generated_asset_sha256)
        if self.retry_parent_asset_sha256 is not None:
            _sha("retry_parent_asset_sha256", self.retry_parent_asset_sha256)
        if self.validation.generated_asset_sha256 != self.generated_asset_sha256:
            raise ContinuityContractError("validation asset hash does not match evidence")


class VideoContinuityContractBinder:
    """Bind approved continuity specs to existing job-scoped reference assets."""

    def __init__(self, reference_assets: ReferenceAssetStore) -> None:
        self._reference_assets = reference_assets

    def plan_shot(
        self,
        *,
        binding: ShotContinuityBinding,
        characters: tuple[CharacterSpec, ...],
        brands: tuple[BrandAssetSpec, ...],
        principal_id: str,
        tenant_id: str,
        capabilities: ProviderContinuityCapabilities,
    ) -> ProviderConditioningPlan:
        _id("principal_id", principal_id)
        _id("tenant_id", tenant_id)
        character_by_id = _unique_map("character", characters, lambda value: value.character_id)
        brand_by_id = _unique_map("brand", brands, lambda value: value.brand_asset_id)
        job_records = self._reference_assets.for_request(binding.job_id)
        job_assets = {record.asset_id: record for record in job_records}

        character_refs: list[str] = []
        native_handles: list[str] = []
        for character_id in binding.character_ids:
            character = character_by_id.get(character_id)
            if character is None:
                raise ContinuityContractError("shot references unknown character_id")
            _ownership(character.tenant_id, character.job_id, tenant_id, binding.job_id)
            if character.strict_identity and not capabilities.supports_subject_references:
                raise ContinuityContractError("provider does not support strict character references")
            records = self._resolve_job_assets(
                character.canonical_reference_asset_ids,
                job_assets=job_assets,
                principal_id=principal_id,
                tenant_id=tenant_id,
                allowed_roles={ReferenceAssetRole.SUBJECT},
            )
            character_refs.extend(record.asset_id for record in records)
            native_handles.extend(character.provider_native_reference_handles)

        provider_brand_refs: list[str] = []
        deterministic_brand_ids: list[str] = []
        for brand_binding in binding.brand_bindings:
            brand = brand_by_id.get(brand_binding.brand_asset_id)
            if brand is None:
                raise ContinuityContractError("shot references unknown brand_asset_id")
            _ownership(brand.tenant_id, brand.job_id, tenant_id, binding.job_id)
            variant = next(
                (item for item in brand.variants if item.variant_id == brand_binding.variant_id),
                None,
            )
            if variant is None:
                raise ContinuityContractError("shot requests unauthorized brand variant")
            records = self._resolve_job_assets(
                (brand.source_reference_asset_id, variant.reference_asset_id),
                job_assets=job_assets,
                principal_id=principal_id,
                tenant_id=tenant_id,
                allowed_roles={ReferenceAssetRole.LOGO},
            )
            source = records[0]
            if source.sha256 != brand.source_sha256:
                raise ContinuityContractError("canonical brand source hash changed")
            if brand_binding.generative_integration_required:
                if not capabilities.supports_brand_references:
                    if brand_binding.strict_fidelity:
                        raise ContinuityContractError(
                            "provider does not support strict brand reference conditioning"
                        )
                    deterministic_brand_ids.append(brand.brand_asset_id)
                else:
                    provider_brand_refs.append(variant.reference_asset_id)
            else:
                deterministic_brand_ids.append(brand.brand_asset_id)

        return ProviderConditioningPlan(
            provider_id=capabilities.provider_id,
            character_reference_asset_ids=tuple(character_refs),
            character_native_handles=tuple(native_handles),
            brand_reference_asset_ids=tuple(provider_brand_refs),
            deterministic_brand_asset_ids=tuple(deterministic_brand_ids),
        )

    def _resolve_job_assets(
        self,
        asset_ids: tuple[str, ...],
        *,
        job_assets: Mapping[str, ReferenceAssetRecord],
        principal_id: str,
        tenant_id: str,
        allowed_roles: set[ReferenceAssetRole],
    ) -> tuple[ReferenceAssetRecord, ...]:
        records: list[ReferenceAssetRecord] = []
        for asset_id in asset_ids:
            record = job_assets.get(asset_id)
            if record is None:
                raise ContinuityContractError("cross-job or unbound reference substitution denied")
            owned = self._reference_assets.get_owned(
                asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            if owned != record:
                raise ContinuityContractError("reference asset ownership/provenance mismatch")
            if owned.role not in allowed_roles:
                raise ContinuityContractError("reference asset role is not authorized for continuity")
            records.append(owned)
        return tuple(records)


def validate_character_continuity(
    *,
    generated_asset: bytes,
    dimension_scores: Mapping[str, float],
    thresholds: Mapping[str, float] = CHARACTER_THRESHOLDS_V1,
) -> ContinuityValidationResult:
    return _validate(
        generated_asset=generated_asset,
        dimension_scores=dimension_scores,
        thresholds=thresholds,
        failure_repair=ContinuityRepair.REGENERATE_SAME_LINEAGE,
    )


def validate_brand_continuity(
    *,
    generated_asset: bytes,
    dimension_scores: Mapping[str, float],
    deterministic_overlay_allowed: bool,
    thresholds: Mapping[str, float] = BRAND_THRESHOLDS_V1,
) -> ContinuityValidationResult:
    return _validate(
        generated_asset=generated_asset,
        dimension_scores=dimension_scores,
        thresholds=thresholds,
        failure_repair=(
            ContinuityRepair.REPLACE_WITH_CANONICAL_OVERLAY
            if deterministic_overlay_allowed
            else ContinuityRepair.REGENERATE_SAME_LINEAGE
        ),
    )


def _validate(
    *,
    generated_asset: bytes,
    dimension_scores: Mapping[str, float],
    thresholds: Mapping[str, float],
    failure_repair: ContinuityRepair,
) -> ContinuityValidationResult:
    if not generated_asset:
        raise ContinuityContractError("generated asset must not be empty")
    if set(dimension_scores) != set(thresholds):
        missing = sorted(set(thresholds) - set(dimension_scores))
        extra = sorted(set(dimension_scores) - set(thresholds))
        raise ContinuityContractError(
            f"continuity dimensions must match versioned contract; missing={missing}, extra={extra}"
        )
    results: list[DimensionResult] = []
    failed: list[str] = []
    for name, threshold in thresholds.items():
        score = dimension_scores[name]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ContinuityContractError("continuity score must be numeric")
        score_value = float(score)
        if score_value < 0.0 or score_value > 1.0:
            raise ContinuityContractError("continuity score must be within [0,1]")
        passed = score_value >= threshold
        results.append(DimensionResult(name, score_value, threshold, passed))
        if not passed:
            failed.append(name)
    digest = sha256(generated_asset).hexdigest()
    verdict = ContinuityVerdict.PASS if not failed else ContinuityVerdict.FAIL
    return ContinuityValidationResult(
        verdict=verdict,
        dimensions=tuple(results),
        generated_asset_sha256=digest,
        failed_dimensions=tuple(failed),
        repair=ContinuityRepair.NONE if not failed else failure_repair,
    )


def _ownership(spec_tenant: str, spec_job: str, tenant_id: str, job_id: str) -> None:
    if spec_tenant != tenant_id or spec_job != job_id:
        raise ContinuityContractError("cross-tenant or cross-job continuity substitution denied")


T = TypeVar("T")


def _unique_map(label: str, values: tuple[T, ...], key: Callable[[T], str]) -> dict[str, T]:
    result: dict[str, T] = {}
    for value in values:
        identifier = key(value)
        if identifier in result:
            raise ContinuityContractError(f"duplicate {label} id")
        result[identifier] = value
    return result


def _id(name: str, value: str) -> None:
    _text(name, value)
    if any(character.isspace() for character in value):
        raise ContinuityContractError(f"{name} must not contain whitespace")


def _text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContinuityContractError(f"{name} must be non-empty text")


def _optional_text(name: str, value: str | None) -> None:
    if value is not None:
        _text(name, value)


def _texts(name: str, values: tuple[str, ...]) -> None:
    for value in values:
        _text(name, value)


def _unique_ids(name: str, values: tuple[str, ...]) -> None:
    _texts(name, values)
    if len(values) != len(set(values)):
        raise ContinuityContractError(f"{name} must not contain duplicates")


def _sha(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContinuityContractError(f"{name} must be lowercase SHA-256")
