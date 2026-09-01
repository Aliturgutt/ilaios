from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidationCoordinator,
    AssembledOutputTechnicalValidationError,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.media_technical_validation import MediaProbeObservation


class _Probe:
    def __init__(self, observation: MediaProbeObservation | None = None) -> None:
        self.observation = observation or _passing_observation()
        self.calls: list[Path] = []

    @property
    def probe_id(self) -> str:
        return "fake-probe-v1"

    def probe(self, path: Path) -> MediaProbeObservation:
        self.calls.append(path)
        return self.observation


def _passing_observation() -> MediaProbeObservation:
    return MediaProbeObservation(
        container="mov,mp4,m4a,3gp,3g2,mj2",
        duration_seconds=10.0,
        width=1080,
        height=1920,
        frames_per_second=24.0,
        video_codec="h264",
        audio_codec="aac",
        video_stream_count=1,
        audio_stream_count=1,
        metadata={"source": "fake"},
    )


def _artifact(path: Path, body: bytes = b"assembled-video") -> EpisodeAssemblyArtifact:
    path.write_bytes(body)
    return EpisodeAssemblyArtifact(
        artifact_id="episode-assembly-artifact-001",
        request_id="episode-assembly-request-001",
        episode_id="episode-001",
        executor_id="fake-executor-v1",
        output_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=24,
        source_asset_ids=("asset-1", "asset-2"),
        metadata={"technical_validation_manifest_id": "media-validation-001"},
    )


def test_coordinator_passes_matching_output(tmp_path: Path) -> None:
    probe = _Probe()
    validation = AssembledOutputTechnicalValidationCoordinator(probe).validate(
        _artifact(tmp_path / "episode.mp4")
    )
    assert validation.status is AssembledOutputTechnicalValidationStatus.PASSED
    assert validation.issues == ()
    assert probe.calls == [tmp_path / "episode.mp4"]


def test_validation_is_deterministic(tmp_path: Path) -> None:
    coordinator = AssembledOutputTechnicalValidationCoordinator(_Probe())
    artifact = _artifact(tmp_path / "episode.mp4")
    first = coordinator.validate(artifact)
    second = coordinator.validate(artifact)
    assert first.validation_id == second.validation_id


def test_missing_output_is_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    Path(artifact.output_path).unlink()
    with pytest.raises(AssembledOutputTechnicalValidationError, match="does not exist"):
        AssembledOutputTechnicalValidationCoordinator(_Probe()).validate(artifact)


def test_byte_length_mismatch_is_rejected(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "episode.mp4")
    Path(artifact.output_path).write_bytes(b"different-size")
    with pytest.raises(AssembledOutputTechnicalValidationError, match="byte length"):
        AssembledOutputTechnicalValidationCoordinator(_Probe()).validate(artifact)


def test_sha256_mismatch_is_rejected(tmp_path: Path) -> None:
    body = b"same-length-data"
    artifact = _artifact(tmp_path / "episode.mp4", body)
    Path(artifact.output_path).write_bytes(b"tampered-content")
    with pytest.raises(AssembledOutputTechnicalValidationError, match="SHA-256"):
        AssembledOutputTechnicalValidationCoordinator(_Probe()).validate(artifact)


def _assert_policy_mismatch(
    tmp_path: Path,
    observation: MediaProbeObservation,
    issue_code: str,
) -> None:
    validation = AssembledOutputTechnicalValidationCoordinator(
        _Probe(observation)
    ).validate(_artifact(tmp_path / "episode.mp4"))
    assert validation.status is AssembledOutputTechnicalValidationStatus.FAILED
    assert issue_code in {issue.code for issue in validation.issues}


def test_container_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="webm",
            duration_seconds=10.0,
            width=1080,
            height=1920,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "container_mismatch",
    )


def test_video_codec_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="mp4",
            duration_seconds=10.0,
            width=1080,
            height=1920,
            frames_per_second=24.0,
            video_codec="hevc",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "video_codec_mismatch",
    )


def test_audio_codec_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="mp4",
            duration_seconds=10.0,
            width=1080,
            height=1920,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="opus",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "audio_codec_mismatch",
    )


def test_width_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="mp4",
            duration_seconds=10.0,
            width=720,
            height=1920,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "width_mismatch",
    )


def test_height_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="mp4",
            duration_seconds=10.0,
            width=1080,
            height=1280,
            frames_per_second=24.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "height_mismatch",
    )


def test_frame_rate_mismatch_is_reported(tmp_path: Path) -> None:
    _assert_policy_mismatch(
        tmp_path,
        MediaProbeObservation(
            container="mp4",
            duration_seconds=10.0,
            width=1080,
            height=1920,
            frames_per_second=30.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        "frame_rate_mismatch",
    )


def test_missing_video_stream_is_reported(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="mp4",
        duration_seconds=10.0,
        width=1080,
        height=1920,
        frames_per_second=24.0,
        video_codec="h264",
        audio_codec="aac",
        video_stream_count=0,
        audio_stream_count=1,
    )
    validation = AssembledOutputTechnicalValidationCoordinator(
        _Probe(observation)
    ).validate(_artifact(tmp_path / "episode.mp4"))
    assert "video_stream_missing" in {
        issue.code for issue in validation.issues
    }


def test_frame_rate_tolerance_is_applied(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="mp4",
        duration_seconds=10.0,
        width=1080,
        height=1920,
        frames_per_second=23.995,
        video_codec="h264",
        audio_codec="aac",
        video_stream_count=1,
        audio_stream_count=1,
    )
    validation = AssembledOutputTechnicalValidationCoordinator(
        _Probe(observation), frame_rate_tolerance=0.01
    ).validate(_artifact(tmp_path / "episode.mp4"))
    assert validation.status is AssembledOutputTechnicalValidationStatus.PASSED


def test_negative_frame_rate_tolerance_is_rejected() -> None:
    with pytest.raises(
        AssembledOutputTechnicalValidationError,
        match="must not be negative",
    ):
        AssembledOutputTechnicalValidationCoordinator(
            _Probe(), frame_rate_tolerance=-0.1
        )


def test_validation_metadata_is_immutable(tmp_path: Path) -> None:
    validation = AssembledOutputTechnicalValidationCoordinator(_Probe()).validate(
        _artifact(tmp_path / "episode.mp4")
    )
    with pytest.raises(TypeError):
        validation.metadata["x"] = "y"  # type: ignore[index]


def test_issue_order_is_deterministic(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="webm",
        duration_seconds=10.0,
        width=720,
        height=1280,
        frames_per_second=30.0,
        video_codec="hevc",
        audio_codec="opus",
        video_stream_count=1,
        audio_stream_count=1,
    )
    validation = AssembledOutputTechnicalValidationCoordinator(
        _Probe(observation)
    ).validate(_artifact(tmp_path / "episode.mp4"))
    codes = tuple(issue.code for issue in validation.issues)
    assert codes == tuple(sorted(codes))
