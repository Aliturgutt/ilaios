from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.request_manifest import (
    EpisodeRequestManifest,
    EpisodeRequestManifestBuilder,
    RequestManifestError,
    ShotRequestEntry,
)
from src.video_automation.shot_request_planning import ShotGenerationRequest


def _request(number: int, *, duration: float = 5.0) -> ShotGenerationRequest:
    suffix = f"{number:02d}"
    return ShotGenerationRequest(
        request_id=f"request-{suffix}",
        idempotency_key=(f"{number:x}" * 64)[:64],
        shot_id=f"episode-001-shot-{suffix}",
        source_beat_id=f"beat-{suffix}",
        prompt_text=f"shot: approved prompt {suffix}",
        duration_seconds=duration,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={"prompt_sha256": "a" * 64},
    )


def test_builder_preserves_explicit_request_order() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(2), _request(1)]
    )
    assert [entry.request.shot_id for entry in manifest.entries] == [
        "episode-001-shot-02",
        "episode-001-shot-01",
    ]


def test_builder_assigns_contiguous_sequence_numbers() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(1), _request(2), _request(3)]
    )
    assert [entry.sequence_number for entry in manifest.entries] == [1, 2, 3]


def test_builder_calculates_count_and_total_duration() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(1, duration=4.5), _request(2, duration=5.5)]
    )
    assert manifest.request_count == 2
    assert manifest.total_duration_seconds == 10.0


def test_manifest_id_is_stable_for_identical_inputs() -> None:
    builder = EpisodeRequestManifestBuilder()
    first = builder.build("episode-001", [_request(1), _request(2)])
    second = builder.build("episode-001", [_request(1), _request(2)])
    assert first.manifest_id == second.manifest_id


def test_request_order_changes_manifest_id() -> None:
    builder = EpisodeRequestManifestBuilder()
    first = builder.build("episode-001", [_request(1), _request(2)])
    second = builder.build("episode-001", [_request(2), _request(1)])
    assert first.manifest_id != second.manifest_id


def test_episode_id_changes_manifest_id() -> None:
    builder = EpisodeRequestManifestBuilder()
    first = builder.build("episode-001", [_request(1)])
    second = builder.build("episode-002", [_request(1)])
    assert first.manifest_id != second.manifest_id


def test_metadata_contains_auditable_boundaries_and_hash() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(1), _request(2)]
    )
    assert manifest.metadata["first_shot_id"] == "episode-001-shot-01"
    assert manifest.metadata["last_shot_id"] == "episode-001-shot-02"
    assert len(manifest.metadata["request_keys_sha256"]) == 64


def test_metadata_is_immutable() -> None:
    manifest = EpisodeRequestManifestBuilder().build("episode-001", [_request(1)])
    assert isinstance(manifest.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        manifest.metadata["new"] = "value"  # type: ignore[index]


def test_builder_rejects_blank_episode_id() -> None:
    with pytest.raises(RequestManifestError, match="episode_id"):
        EpisodeRequestManifestBuilder().build(" ", [_request(1)])


def test_builder_rejects_empty_request_collection() -> None:
    with pytest.raises(RequestManifestError, match="requests"):
        EpisodeRequestManifestBuilder().build("episode-001", [])


def test_builder_rejects_duplicate_request_ids() -> None:
    request = _request(1)
    with pytest.raises(RequestManifestError, match="request_id"):
        EpisodeRequestManifestBuilder().build("episode-001", [request, request])


def test_builder_rejects_duplicate_shot_ids() -> None:
    first = _request(1)
    second = ShotGenerationRequest(
        request_id="request-02",
        idempotency_key="b" * 64,
        shot_id=first.shot_id,
        source_beat_id="beat-02",
        prompt_text="shot: second",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={},
    )
    with pytest.raises(RequestManifestError, match="shot_id"):
        EpisodeRequestManifestBuilder().build("episode-001", [first, second])


def test_entry_rejects_non_positive_sequence_number() -> None:
    with pytest.raises(RequestManifestError, match="sequence_number"):
        ShotRequestEntry(sequence_number=0, request=_request(1))


def test_manifest_rejects_non_contiguous_sequence() -> None:
    with pytest.raises(RequestManifestError, match="contiguous"):
        EpisodeRequestManifest(
            manifest_id="manifest-1",
            episode_id="episode-001",
            entries=(ShotRequestEntry(2, _request(1)),),
            total_duration_seconds=5.0,
            request_count=1,
            metadata={},
        )


def test_manifest_rejects_incorrect_request_count() -> None:
    with pytest.raises(RequestManifestError, match="request_count"):
        EpisodeRequestManifest(
            manifest_id="manifest-1",
            episode_id="episode-001",
            entries=(ShotRequestEntry(1, _request(1)),),
            total_duration_seconds=5.0,
            request_count=2,
            metadata={},
        )


def test_manifest_copies_metadata_before_freezing() -> None:
    metadata = {"key": "value"}
    manifest = EpisodeRequestManifest(
        manifest_id="manifest-1",
        episode_id="episode-001",
        entries=(ShotRequestEntry(1, _request(1)),),
        total_duration_seconds=5.0,
        request_count=1,
        metadata=metadata,
    )
    metadata["key"] = "changed"
    assert manifest.metadata["key"] == "value"


def test_manifest_contains_no_provider_or_execution_result() -> None:
    manifest = EpisodeRequestManifestBuilder().build("episode-001", [_request(1)])
    assert not hasattr(manifest, "provider")
    assert not hasattr(manifest, "result")
