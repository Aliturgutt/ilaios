"""Tests for canonical M21 Render Technical Validation."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from src.video_automation.ffmpeg_media_engine import MediaProbe
from src.video_automation.models import RenderArtifact
from src.video_automation.render_technical_validation import (
    RenderTechnicalValidationProfile,
    RenderTechnicalValidationStatus,
    RenderTechnicalValidator,
)


def _profile() -> RenderTechnicalValidationProfile:
    return RenderTechnicalValidationProfile(
        allowed_containers=(
            "mov,mp4,m4a,3gp,3g2,mj2",
            "mp4",
        ),
        allowed_video_codecs=(
            "h264",
            "hevc",
        ),
        allowed_audio_codecs=(
            "aac",
        ),
        expected_width=720,
        expected_height=1280,
        expected_duration_seconds=40.0,
        duration_tolerance_seconds=0.25,
        expected_fps=30.0,
        fps_tolerance=0.05,
        require_audio_stream=True,
        expected_aspect_ratio="9:16",
        min_size_bytes=4,
        max_size_bytes=100_000_000,
    )


def _artifact(
    path: Path,
    *,
    codec: str = "h264",
    audio_codec: str = "aac",
    resolution: str = "720x1280",
    duration_seconds: float = 40.0,
    fps: float = 30.0,
    aspect_ratio: str = "9:16",
) -> RenderArtifact:
    body = path.read_bytes()

    return RenderArtifact(
        artifact_id="render-artifact-1",
        job_id="job-1",
        file_path=str(
            path.resolve()
        ),
        checksum_sha256=sha256(
            body
        ).hexdigest(),
        codec=codec,
        resolution=resolution,
        duration_seconds=duration_seconds,
        fps=fps,
        audio_codec=audio_codec,
        aspect_ratio=aspect_ratio,
        size_bytes=len(body),
    )


class _Probe:
    def __init__(
        self,
        *,
        container: str = "mov,mp4,m4a,3gp,3g2,mj2",
        video_codec: str = "h264",
        audio_codec: str | None = "aac",
        width: int = 720,
        height: int = 1280,
        duration_seconds: float = 40.0,
        fps: str = "30/1",
        extra_video_stream: bool = False,
    ) -> None:
        self.container = container
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.width = width
        self.height = height
        self.duration_seconds = duration_seconds
        self.fps = fps
        self.extra_video_stream = extra_video_stream

    def probe(
        self,
        path: str | Path,
    ) -> MediaProbe:
        streams: list[dict[str, object]] = [
            {
                "codec_type": "video",
                "codec_name": self.video_codec,
                "width": self.width,
                "height": self.height,
                "avg_frame_rate": self.fps,
            }
        ]

        if self.extra_video_stream:
            streams.append(
                {
                    "codec_type": "video",
                    "codec_name": self.video_codec,
                    "width": self.width,
                    "height": self.height,
                    "avg_frame_rate": self.fps,
                }
            )

        if self.audio_codec is not None:
            streams.append(
                {
                    "codec_type": "audio",
                    "codec_name": self.audio_codec,
                }
            )

        return MediaProbe(
            path=str(
                Path(path).resolve()
            ),
            format_name=self.container,
            duration_seconds=self.duration_seconds,
            streams=tuple(streams),
        )


def test_valid_render_artifact_passes_all_m21_checks() -> None:
    with TemporaryDirectory() as directory_name:
        path = (
            Path(directory_name)
            / "final.mp4"
        )

        path.write_bytes(
            b"valid-render"
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(),
            profile=_profile(),
        ).validate(
            _artifact(path)
        )

        assert (
            result.status
            is RenderTechnicalValidationStatus.PASSED
        )

        assert result.issues == ()
        assert result.observed_width == 720
        assert result.observed_height == 1280
        assert result.observed_fps == 30.0
        assert result.observed_aspect_ratio == "9:16"


def test_validation_is_deterministic() -> None:
    with TemporaryDirectory() as directory_name:
        path = (
            Path(directory_name)
            / "final.mp4"
        )

        path.write_bytes(
            b"valid-render"
        )

        artifact = _artifact(
            path
        )

        validator = RenderTechnicalValidator(
            probe_engine=_Probe(),
            profile=_profile(),
        )

        first = validator.validate(
            artifact
        )
        second = validator.validate(
            artifact
        )

        assert first == second


def test_container_failure_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                container="matroska,webm",
            ),
            profile=_profile(),
        ).validate(
            _artifact(path)
        )

        assert (
            result.status
            is RenderTechnicalValidationStatus.FAILED
        )

        assert "container_not_allowed" in {
            issue.code
            for issue in result.issues
        }


def test_resolution_failure_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        artifact = _artifact(
            path,
            resolution="1080x1920",
            aspect_ratio="9:16",
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                width=1080,
                height=1920,
            ),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "resolution_mismatch" in {
            issue.code
            for issue in result.issues
        }


def test_duration_failure_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        artifact = _artifact(
            path,
            duration_seconds=42.0,
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                duration_seconds=42.0,
            ),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "duration_mismatch" in {
            issue.code
            for issue in result.issues
        }


def test_fps_failure_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        artifact = _artifact(
            path,
            fps=24.0,
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                fps="24/1",
            ),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "fps_mismatch" in {
            issue.code
            for issue in result.issues
        }


def test_missing_audio_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                audio_codec=None,
            ),
            profile=_profile(),
        ).validate(
            _artifact(path)
        )

        codes = {
            issue.code
            for issue in result.issues
        }

        assert "audio_stream_integrity" in codes
        assert "audio_codec_not_allowed" in codes


def test_multiple_video_streams_fail_integrity() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                extra_video_stream=True,
            ),
            profile=_profile(),
        ).validate(
            _artifact(path)
        )

        assert "video_stream_integrity" in {
            issue.code
            for issue in result.issues
        }


def test_checksum_mutation_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"original")

        artifact = _artifact(
            path
        )

        path.write_bytes(
            b"mutated!"
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "artifact_checksum_mismatch" in {
            issue.code
            for issue in result.issues
        }


def test_size_metadata_mismatch_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        artifact = _artifact(
            path
        )

        object.__setattr__(
            artifact,
            "size_bytes",
            artifact.size_bytes + 1,
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "artifact_size_mismatch" in {
            issue.code
            for issue in result.issues
        }


def test_video_codec_mismatch_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"valid-render")

        result = RenderTechnicalValidator(
            probe_engine=_Probe(
                video_codec="vp9",
            ),
            profile=_profile(),
        ).validate(
            _artifact(path)
        )

        codes = {
            issue.code
            for issue in result.issues
        }

        assert "video_codec_not_allowed" in codes
        assert "artifact_video_codec_mismatch" in codes


def test_file_size_boundary_failure_is_reported() -> None:
    with TemporaryDirectory() as directory_name:
        path = Path(directory_name) / "final.mp4"
        path.write_bytes(b"x")

        artifact = _artifact(
            path
        )

        result = RenderTechnicalValidator(
            probe_engine=_Probe(),
            profile=_profile(),
        ).validate(
            artifact
        )

        assert "file_size_below_minimum" in {
            issue.code
            for issue in result.issues
        }
