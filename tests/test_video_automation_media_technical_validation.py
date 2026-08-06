from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.generated_asset_retrieval import (
    EpisodeGeneratedAssetRetrievalManifest,
    RetrievedGenerationAsset,
)
from src.video_automation.media_technical_validation import (
    FfprobeMediaTechnicalProbe,
    MediaProbeObservation,
    MediaTechnicalProfile,
    MediaTechnicalValidationCoordinator,
    MediaTechnicalValidationError,
    MediaTechnicalValidationStatus,
)


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
        duration_seconds=5.0,
        width=1080,
        height=1920,
        frames_per_second=24.0,
        video_codec="h264",
        audio_codec="aac",
        video_stream_count=1,
        audio_stream_count=1,
        metadata={"source": "fake"},
    )


def _retrieval_manifest(path: Path, body: bytes = b"video-bytes") -> EpisodeGeneratedAssetRetrievalManifest:
    path.write_bytes(body)
    asset = RetrievedGenerationAsset(
        asset_id="https://assets.test/video.mp4",
        dispatch_id="dispatch-001",
        provider_job_id="job-001",
        provider_id="provider-alpha",
        batch_number=1,
        output_index=1,
        local_path=str(path),
        sha256_hex=sha256(body).hexdigest(),
        byte_length=len(body),
        content_type="video/mp4",
        metadata={"source_asset_id": "https://assets.test/video.mp4"},
    )
    return EpisodeGeneratedAssetRetrievalManifest(
        retrieval_manifest_id="asset-retrieval-001",
        result_manifest_id="result-manifest-001",
        dispatch_plan_id="dispatch-plan-001",
        episode_id="episode-001",
        assets=(asset,),
        asset_count=1,
        metadata={"storage_root": str(path.parent)},
    )


def test_profile_rejects_invalid_range() -> None:
    with pytest.raises(MediaTechnicalValidationError, match="min_width"):
        MediaTechnicalProfile(min_width=2000, max_width=1000)


def test_observation_metadata_is_immutable() -> None:
    observation = _passing_observation()
    with pytest.raises(TypeError):
        observation.metadata["x"] = "y"  # type: ignore[index]


def test_coordinator_passes_compliant_asset(tmp_path: Path) -> None:
    probe = _Probe()
    manifest = MediaTechnicalValidationCoordinator(probe).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    assert manifest.status is MediaTechnicalValidationStatus.PASSED
    assert manifest.passed_count == 1
    assert manifest.failed_count == 0
    assert manifest.assets[0].issues == ()
    assert probe.calls == [tmp_path / "video.mp4"]


def test_coordinator_fails_noncompliant_asset(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="webm",
        duration_seconds=5.0,
        width=640,
        height=360,
        frames_per_second=15.0,
        video_codec="mpeg4",
        audio_codec=None,
        video_stream_count=1,
        audio_stream_count=0,
    )
    manifest = MediaTechnicalValidationCoordinator(_Probe(observation)).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    codes = {issue.code for issue in manifest.assets[0].issues}
    assert manifest.status is MediaTechnicalValidationStatus.FAILED
    assert {
        "container_not_allowed",
        "video_codec_not_allowed",
        "width_below_minimum",
        "height_below_minimum",
        "fps_below_minimum",
    }.issubset(codes)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing.mp4"
    manifest = _retrieval_manifest(tmp_path / "source.mp4")
    asset = manifest.assets[0]
    missing_asset = RetrievedGenerationAsset(
        asset_id=asset.asset_id,
        dispatch_id=asset.dispatch_id,
        provider_job_id=asset.provider_job_id,
        provider_id=asset.provider_id,
        batch_number=asset.batch_number,
        output_index=asset.output_index,
        local_path=str(path),
        sha256_hex=asset.sha256_hex,
        byte_length=asset.byte_length,
        content_type=asset.content_type,
    )
    broken = EpisodeGeneratedAssetRetrievalManifest(
        retrieval_manifest_id=manifest.retrieval_manifest_id,
        result_manifest_id=manifest.result_manifest_id,
        dispatch_plan_id=manifest.dispatch_plan_id,
        episode_id=manifest.episode_id,
        assets=(missing_asset,),
        asset_count=1,
    )
    with pytest.raises(MediaTechnicalValidationError, match="does not exist"):
        MediaTechnicalValidationCoordinator(_Probe()).validate(broken)


def test_byte_length_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = _retrieval_manifest(tmp_path / "video.mp4")
    Path(manifest.assets[0].local_path).write_bytes(b"different-size")
    with pytest.raises(MediaTechnicalValidationError, match="byte length"):
        MediaTechnicalValidationCoordinator(_Probe()).validate(manifest)


def test_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    body = b"same-length"
    manifest = _retrieval_manifest(tmp_path / "video.mp4", body)
    Path(manifest.assets[0].local_path).write_bytes(b"other-data!")
    with pytest.raises(MediaTechnicalValidationError, match="SHA-256"):
        MediaTechnicalValidationCoordinator(_Probe()).validate(manifest)


def test_audio_can_be_disallowed(tmp_path: Path) -> None:
    profile = MediaTechnicalProfile(allow_audio_stream=False)
    manifest = MediaTechnicalValidationCoordinator(_Probe(), profile).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    assert [issue.code for issue in manifest.assets[0].issues] == [
        "audio_stream_not_allowed"
    ]


def test_missing_video_stream_fails(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="mp4",
        duration_seconds=5.0,
        width=0,
        height=0,
        frames_per_second=0.0,
        video_codec="none",
        audio_codec="aac",
        video_stream_count=0,
        audio_stream_count=1,
    )
    manifest = MediaTechnicalValidationCoordinator(_Probe(observation)).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    codes = {issue.code for issue in manifest.assets[0].issues}
    assert "video_stream_missing" in codes


def test_duration_tolerance_is_applied(tmp_path: Path) -> None:
    observation = MediaProbeObservation(
        container="mp4",
        duration_seconds=4.8,
        width=1080,
        height=1920,
        frames_per_second=24.0,
        video_codec="h264",
        audio_codec=None,
        video_stream_count=1,
        audio_stream_count=0,
    )
    profile = MediaTechnicalProfile(
        min_duration_seconds=5.0,
        max_duration_seconds=5.0,
        duration_tolerance_seconds=0.25,
    )
    manifest = MediaTechnicalValidationCoordinator(_Probe(observation), profile).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    assert manifest.status is MediaTechnicalValidationStatus.PASSED


def test_manifest_is_deterministic(tmp_path: Path) -> None:
    coordinator = MediaTechnicalValidationCoordinator(_Probe())
    retrieval = _retrieval_manifest(tmp_path / "video.mp4")
    first = coordinator.validate(retrieval)
    second = coordinator.validate(retrieval)
    assert (
        first.technical_validation_manifest_id
        == second.technical_validation_manifest_id
    )
    assert first.assets[0].evidence_id == second.assets[0].evidence_id


def test_manifest_metadata_is_immutable(tmp_path: Path) -> None:
    manifest = MediaTechnicalValidationCoordinator(_Probe()).validate(
        _retrieval_manifest(tmp_path / "video.mp4")
    )
    with pytest.raises(TypeError):
        manifest.metadata["x"] = "y"  # type: ignore[index]


def test_ffprobe_adapter_parses_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload: Mapping[str, object] = {
        "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "5.000000",
        },
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1080,
                "height": 1920,
                "avg_frame_rate": "24/1",
                "r_frame_rate": "24/1",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
            },
        ],
    }

    def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["ffprobe"], returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _run)
    observation = FfprobeMediaTechnicalProbe().probe(tmp_path / "video.mp4")
    assert observation.video_codec == "h264"
    assert observation.frames_per_second == 24.0
    assert observation.audio_codec == "aac"


def test_ffprobe_adapter_rejects_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["ffprobe"], returncode=1, stdout="", stderr="invalid data"
        )

    monkeypatch.setattr(subprocess, "run", _run)
    with pytest.raises(MediaTechnicalValidationError, match="invalid data"):
        FfprobeMediaTechnicalProbe().probe(tmp_path / "video.mp4")


def test_ffprobe_adapter_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["ffprobe"], returncode=0, stdout="{bad", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _run)
    with pytest.raises(MediaTechnicalValidationError, match="invalid JSON"):
        FfprobeMediaTechnicalProbe().probe(tmp_path / "video.mp4")


def test_ffprobe_adapter_handles_audio_only_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "format": {"format_name": "mp4", "duration": "5.0"},
        "streams": [
            {"index": 0, "codec_type": "audio", "codec_name": "aac"}
        ],
    }

    def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["ffprobe"], returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _run)
    observation = FfprobeMediaTechnicalProbe().probe(tmp_path / "audio.mp4")
    assert observation.video_stream_count == 0
    assert observation.video_codec == "none"


def test_profile_values_are_normalized() -> None:
    profile = MediaTechnicalProfile(
        allowed_containers=("MP4",),
        allowed_video_codecs=("H264",),
    )
    assert profile.allowed_containers == ("mp4",)
    assert profile.allowed_video_codecs == ("h264",)
