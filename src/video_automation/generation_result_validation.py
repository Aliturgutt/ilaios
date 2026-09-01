"""Deterministic validation of ingested generation result assets.

This module consumes an immutable generation result manifest together with
explicit validation observations supplied by an external validator. It does
not inspect media, call providers, infer quality, retry work, or modify assets.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType

from .generation_result_ingestion import EpisodeGenerationResultManifest


class GenerationResultValidationError(ValueError):
    """Raised when explicit result validation data is inconsistent or invalid."""


class GenerationAssetValidationStatus(StrEnum):
    """Allowed explicit validation outcomes for one generated asset."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class GenerationAssetValidationObservation:
    """Externally supplied validation observation for one generated asset."""

    asset_id: str
    status: GenerationAssetValidationStatus
    checks: tuple[str, ...]
    rejection_code: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("asset_id", self.asset_id)
        _validate_checks(self.checks)
        _validate_optional_non_blank("rejection_code", self.rejection_code)
        if self.status is GenerationAssetValidationStatus.ACCEPTED:
            if self.rejection_code is not None:
                raise GenerationResultValidationError(
                    "accepted observation must not contain rejection_code"
                )
        elif self.rejection_code is None:
            raise GenerationResultValidationError(
                "rejected observation must contain rejection_code"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ValidatedGenerationAsset:
    """Immutable validation result aligned with one ingested generation asset."""

    asset_id: str
    dispatch_id: str
    provider_job_id: str
    batch_number: int
    output_index: int
    status: GenerationAssetValidationStatus
    checks: tuple[str, ...]
    rejection_code: str | None
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_job_id", self.provider_job_id)
        if self.batch_number <= 0:
            raise GenerationResultValidationError(
                "batch_number must be greater than zero"
            )
        if self.output_index <= 0:
            raise GenerationResultValidationError(
                "output_index must be greater than zero"
            )
        _validate_checks(self.checks)
        _validate_optional_non_blank("rejection_code", self.rejection_code)
        if self.status is GenerationAssetValidationStatus.ACCEPTED:
            if self.rejection_code is not None:
                raise GenerationResultValidationError(
                    "accepted result must not contain rejection_code"
                )
        elif self.rejection_code is None:
            raise GenerationResultValidationError(
                "rejected result must contain rejection_code"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeGenerationValidationManifest:
    """Immutable validation manifest for one generation result manifest."""

    validation_manifest_id: str
    result_manifest_id: str
    execution_state_id: str
    episode_id: str
    assets: tuple[ValidatedGenerationAsset, ...]
    accepted_count: int
    rejected_count: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("validation_manifest_id", self.validation_manifest_id)
        _require_non_blank("result_manifest_id", self.result_manifest_id)
        _require_non_blank("execution_state_id", self.execution_state_id)
        _require_non_blank("episode_id", self.episode_id)
        if self.accepted_count < 0:
            raise GenerationResultValidationError("accepted_count must not be negative")
        if self.rejected_count < 0:
            raise GenerationResultValidationError("rejected_count must not be negative")
        if self.accepted_count + self.rejected_count != len(self.assets):
            raise GenerationResultValidationError(
                "validation counts must equal asset count"
            )
        asset_ids = tuple(asset.asset_id for asset in self.assets)
        if len(asset_ids) != len(set(asset_ids)):
            raise GenerationResultValidationError("validated asset_ids must be unique")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def all_accepted(self) -> bool:
        """Return whether every generated asset was explicitly accepted."""

        return self.rejected_count == 0


class EpisodeGenerationResultValidator:
    """Validate result assets using only explicit external observations."""

    def validate(
        self,
        result_manifest: EpisodeGenerationResultManifest,
        observations: tuple[GenerationAssetValidationObservation, ...],
    ) -> EpisodeGenerationValidationManifest:
        """Build a deterministic validation manifest without inspecting media."""

        expected_ids = tuple(asset.asset_id for asset in result_manifest.assets)
        observed_ids = tuple(observation.asset_id for observation in observations)
        if observed_ids != expected_ids:
            raise GenerationResultValidationError(
                "validation observations must match result asset order exactly"
            )
        if len(observed_ids) != len(set(observed_ids)):
            raise GenerationResultValidationError(
                "validation observation asset_ids must be unique"
            )

        validated = tuple(
            ValidatedGenerationAsset(
                asset_id=asset.asset_id,
                dispatch_id=asset.dispatch_id,
                provider_job_id=asset.provider_job_id,
                batch_number=asset.batch_number,
                output_index=asset.output_index,
                status=observation.status,
                checks=observation.checks,
                rejection_code=observation.rejection_code,
                metadata=observation.metadata,
            )
            for asset, observation in zip(
                result_manifest.assets, observations, strict=True
            )
        )
        canonical = _canonical_validation_material(result_manifest, validated)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        accepted_count = sum(
            item.status is GenerationAssetValidationStatus.ACCEPTED
            for item in validated
        )
        rejected_count = len(validated) - accepted_count
        return EpisodeGenerationValidationManifest(
            validation_manifest_id=f"generation-validation-{digest[:16]}",
            result_manifest_id=result_manifest.result_manifest_id,
            execution_state_id=result_manifest.execution_state_id,
            episode_id=result_manifest.episode_id,
            assets=validated,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            metadata={"asset_count": str(len(validated))},
        )


def _canonical_validation_material(
    result_manifest: EpisodeGenerationResultManifest,
    assets: tuple[ValidatedGenerationAsset, ...],
) -> str:
    lines = [
        f"result_manifest_id={result_manifest.result_manifest_id}",
        f"execution_state_id={result_manifest.execution_state_id}",
        f"episode_id={result_manifest.episode_id}",
    ]
    lines.extend(
        f"asset_id={asset.asset_id}|status={asset.status.value}|"
        f"checks={','.join(asset.checks)}|rejection_code={asset.rejection_code or ''}"
        for asset in assets
    )
    return "\n".join(lines)


def _validate_checks(checks: tuple[str, ...]) -> None:
    if not checks:
        raise GenerationResultValidationError("checks must not be empty")
    if len(checks) != len(set(checks)):
        raise GenerationResultValidationError("checks must be unique")
    for check in checks:
        _require_non_blank("check", check)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(normalized)


def _validate_optional_non_blank(name: str, value: str | None) -> None:
    if value is not None:
        _require_non_blank(name, value)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationResultValidationError(f"{name} must not be blank")
