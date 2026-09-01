from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.generation_result_ingestion import (
    EpisodeGenerationResultManifest,
    GenerationResultAsset,
)
from src.video_automation.generation_result_validation import (
    EpisodeGenerationResultValidator,
    EpisodeGenerationValidationManifest,
    GenerationAssetValidationObservation,
    GenerationAssetValidationStatus,
    GenerationResultValidationError,
    ValidatedGenerationAsset,
)


def _asset(number: int) -> GenerationResultAsset:
    return GenerationResultAsset(
        asset_id=f"asset-{number:02d}",
        dispatch_id=f"dispatch-{number:02d}",
        provider_job_id=f"job-{number:02d}",
        batch_number=number,
        output_index=1,
        metadata={},
    )


def _manifest(count: int = 2) -> EpisodeGenerationResultManifest:
    assets = tuple(_asset(number) for number in range(1, count + 1))
    return EpisodeGenerationResultManifest(
        result_manifest_id="generation-result-001",
        execution_state_id="execution-state-001",
        dispatch_plan_id="dispatch-plan-001",
        generation_plan_id="generation-plan-001",
        request_manifest_id="request-manifest-001",
        episode_id="episode-001",
        assets=assets,
        dispatch_count=max(count, 1),
        succeeded_count=max(count, 1),
        failed_count=0,
        cancelled_count=0,
        metadata={},
    )


def _accepted(asset_id: str) -> GenerationAssetValidationObservation:
    return GenerationAssetValidationObservation(
        asset_id=asset_id,
        status=GenerationAssetValidationStatus.ACCEPTED,
        checks=("duration", "decode"),
        metadata={"validator": "external"},
    )


def test_validate_preserves_result_asset_order() -> None:
    manifest = _manifest()
    result = EpisodeGenerationResultValidator().validate(
        manifest, tuple(_accepted(asset.asset_id) for asset in manifest.assets)
    )
    assert [asset.asset_id for asset in result.assets] == ["asset-01", "asset-02"]


def test_validate_copies_source_asset_identity() -> None:
    manifest = _manifest(1)
    result = EpisodeGenerationResultValidator().validate(
        manifest, (_accepted("asset-01"),)
    )
    asset = result.assets[0]
    assert asset.dispatch_id == "dispatch-01"
    assert asset.provider_job_id == "job-01"
    assert asset.batch_number == 1
    assert asset.output_index == 1


def test_validate_counts_accepted_and_rejected() -> None:
    manifest = _manifest()
    observations = (
        _accepted("asset-01"),
        GenerationAssetValidationObservation(
            "asset-02",
            GenerationAssetValidationStatus.REJECTED,
            ("duration",),
            "duration_mismatch",
            {},
        ),
    )
    result = EpisodeGenerationResultValidator().validate(manifest, observations)
    assert result.accepted_count == 1
    assert result.rejected_count == 1
    assert result.all_accepted is False


def test_validate_all_accepted_property() -> None:
    manifest = _manifest()
    result = EpisodeGenerationResultValidator().validate(
        manifest, tuple(_accepted(asset.asset_id) for asset in manifest.assets)
    )
    assert result.all_accepted is True


def test_validate_is_deterministic() -> None:
    manifest = _manifest(1)
    observations = (_accepted("asset-01"),)
    validator = EpisodeGenerationResultValidator()
    assert validator.validate(manifest, observations).validation_manifest_id == (
        validator.validate(manifest, observations).validation_manifest_id
    )


def test_validate_rejects_missing_observation() -> None:
    with pytest.raises(GenerationResultValidationError, match="match result asset order"):
        EpisodeGenerationResultValidator().validate(_manifest(), (_accepted("asset-01"),))


def test_validate_rejects_reordered_observations() -> None:
    observations = (_accepted("asset-02"), _accepted("asset-01"))
    with pytest.raises(GenerationResultValidationError, match="match result asset order"):
        EpisodeGenerationResultValidator().validate(_manifest(), observations)


def test_validate_rejects_unknown_asset() -> None:
    observations = (_accepted("asset-01"), _accepted("asset-99"))
    with pytest.raises(GenerationResultValidationError, match="match result asset order"):
        EpisodeGenerationResultValidator().validate(_manifest(), observations)


def test_observation_rejects_empty_checks() -> None:
    with pytest.raises(GenerationResultValidationError, match="checks"):
        GenerationAssetValidationObservation(
            "asset-01", GenerationAssetValidationStatus.ACCEPTED, (), None, {}
        )


def test_observation_rejects_duplicate_checks() -> None:
    with pytest.raises(GenerationResultValidationError, match="unique"):
        GenerationAssetValidationObservation(
            "asset-01",
            GenerationAssetValidationStatus.ACCEPTED,
            ("decode", "decode"),
            None,
            {},
        )


def test_accepted_observation_rejects_rejection_code() -> None:
    with pytest.raises(GenerationResultValidationError, match="must not contain"):
        GenerationAssetValidationObservation(
            "asset-01",
            GenerationAssetValidationStatus.ACCEPTED,
            ("decode",),
            "unexpected",
            {},
        )


def test_rejected_observation_requires_rejection_code() -> None:
    with pytest.raises(GenerationResultValidationError, match="must contain"):
        GenerationAssetValidationObservation(
            "asset-01",
            GenerationAssetValidationStatus.REJECTED,
            ("decode",),
            None,
            {},
        )


def test_observation_metadata_is_immutable() -> None:
    observation = _accepted("asset-01")
    assert isinstance(observation.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        observation.metadata["validator"] = "changed"  # type: ignore[index]


def test_validated_asset_metadata_is_immutable() -> None:
    asset = ValidatedGenerationAsset(
        "asset-01",
        "dispatch-01",
        "job-01",
        1,
        1,
        GenerationAssetValidationStatus.ACCEPTED,
        ("decode",),
        None,
        {"validator": "external"},
    )
    assert isinstance(asset.metadata, MappingProxyType)


def test_validation_manifest_rejects_inconsistent_counts() -> None:
    with pytest.raises(GenerationResultValidationError, match="must equal"):
        EpisodeGenerationValidationManifest(
            "validation-01",
            "result-01",
            "state-01",
            "episode-01",
            (),
            1,
            0,
            {},
        )


def test_validation_manifest_metadata_is_immutable() -> None:
    manifest = _manifest(1)
    result = EpisodeGenerationResultValidator().validate(
        manifest, (_accepted("asset-01"),)
    )
    assert isinstance(result.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        result.metadata["asset_count"] = "2"  # type: ignore[index]


def test_validate_empty_result_manifest_with_empty_observations() -> None:
    manifest = EpisodeGenerationResultManifest(
        "generation-result-empty",
        "execution-state-001",
        "dispatch-plan-001",
        "generation-plan-001",
        "request-manifest-001",
        "episode-001",
        (),
        1,
        0,
        1,
        0,
        {},
    )
    result = EpisodeGenerationResultValidator().validate(manifest, ())
    assert result.assets == ()
    assert result.accepted_count == 0
    assert result.rejected_count == 0
