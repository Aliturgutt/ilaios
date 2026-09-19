"""Service-layer binding for Video Factory continuity contracts.

This adapter is the only continuity layer that touches the canonical ReferenceAssetStore.
Pure Character/Brand contracts stay under ``src.video_automation`` so dependency direction
remains src -> no services, while services may compose both existing authorities.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Mapping, TypeVar

from services.reference_assets import (
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)
from src.video_automation.continuity_contracts import (
    BrandAssetSpec,
    CharacterSpec,
    ContinuityContractError,
    ProviderConditioningPlan,
    ProviderContinuityCapabilities,
    ShotContinuityBinding,
)


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


T = TypeVar("T")


def _unique_map(label: str, values: tuple[T, ...], key: Callable[[T], str]) -> dict[str, T]:
    result: dict[str, T] = {}
    for value in values:
        identifier = key(value)
        if identifier in result:
            raise ContinuityContractError(f"duplicate {label} id")
        result[identifier] = value
    return result


def _ownership(spec_tenant: str, spec_job: str, tenant_id: str, job_id: str) -> None:
    if spec_tenant != tenant_id or spec_job != job_id:
        raise ContinuityContractError("cross-tenant or cross-job continuity substitution denied")


def _id(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContinuityContractError(f"{name} must be non-empty text")
    if any(character.isspace() for character in value):
        raise ContinuityContractError(f"{name} must not contain whitespace")
