from __future__ import annotations

import shutil
import subprocess
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from services.integrations.video_skill_governance import approve_video_skills
from services.integrations.video_thumbnail import GovernedThumbnailExecutor
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalIssue,
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.ffmpeg_media_engine import MediaCommandResult
from src.video_automation.media_technical_validation import MediaProbeObservation
from src.video_automation.thumbnail_generation import (
    FfmpegThumbnailRenderer,
    ThumbnailGenerationCoordinator,
    ThumbnailGenerationError,
)
from src.video_automation.video_quality import QaObservationSource
from src.video_automation.video_quality_observations import (
    technical_observation_from_assembled_validation,
)
from src.video_automation.video_skills import QaDomain, ThumbnailRequest


class _RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> MediaCommandResult:
        assert timeout_seconds > 0
        self.calls.append(argv)
        return MediaCommandResult(argv=argv, return_code=0, stdout="", stderr="")


class _WritingRenderer:
    def __init__(self, *, renders_text: bool = True) -> None:
        self.calls = 0
        self._renders_text = renders_text

    @property
    def renderer_id(self) -> str:
        return "test-thumbnail-renderer-v1"

    @property
    def renders_text(self) -> bool:
        return self._renders_text

    def render(
        self,
        *,
        source_path: Path,
        output_path: Path,
        timestamp_ms: int,
        width: int,
        height: int,
        safe_text: str,
    ) -> None:
        assert source_path.is_file()
        assert timestamp_ms >= 0
        assert width > 0 and height > 0
        self.calls += 1
        output_path.write_bytes(
            f"jpeg:{timestamp_ms}:{width}:{height}:{safe_text}".encode("utf-8")
        )


class _NoOutputRenderer:
    @property
    def renderer_id(self) -> str:
        return "no-output-renderer-v1"

    @property
    def renders_text(self) -> bool:
        return True

    def render(
        self,
        *,
        source_path: Path,
        output_path: Path,
        timestamp_ms: int,
        width: int,
        height: int,
        safe_text: str,
    ) -> None:
        return None


def _source(root: Path) -> tuple[Path, bytes, str]:
    body = b"canonical-video-artifact"
    path = root / "episode.mp4"
    path.write_bytes(body)
    return path, body, sha256(body).hexdigest()


def _request(source_sha: str, *, safe_text: str = "") -> ThumbnailRequest:
    return ThumbnailRequest(
        request_id="thumbnail-request-001",
        artifact_sha256=source_sha,
        timestamp_ms=500,
        width=120,
        height=120,
        safe_text=safe_text,
    )


def _technical_validation(
    *,
    passed: bool,
    artifact_sha: str = "a" * 64,
) -> AssembledOutputTechnicalValidation:
    observation = MediaProbeObservation(
        container="mp4",
        duration_seconds=4.0,
        width=1080,
        height=1920,
        frames_per_second=30.0,
        video_codec="h264",
        audio_codec="aac",
        video_stream_count=1,
        audio_stream_count=1,
    )
    issues = (
        ()
        if passed
        else (
            AssembledOutputTechnicalIssue(
                "frame_rate_mismatch",
                "observed frame rate violates the assembly contract",
            ),
        )
    )
    return AssembledOutputTechnicalValidation(
        validation_id="assembled-validation-001",
        artifact_id="assembled-artifact-001",
        request_id="assembly-request-001",
        episode_id="episode-001",
        output_path="/evidence/episode.mp4",
        sha256_hex=artifact_sha,
        byte_length=1024,
        status=(
            AssembledOutputTechnicalValidationStatus.PASSED
            if passed
            else AssembledOutputTechnicalValidationStatus.FAILED
        ),
        observation=observation,
        issues=issues,
        probe_id="ffprobe-json-v1",
        metadata={"executor_id": "video-producer"},
    )


def test_passed_technical_validation_becomes_exact_artifact_qa_observation() -> None:
    validation = _technical_validation(passed=True)
    observation = technical_observation_from_assembled_validation(
        validation,
        observer_id="technical-observer",
        producer_id="video-producer",
    )
    assert observation.domain is QaDomain.TECHNICAL
    assert observation.source is QaObservationSource.DETERMINISTIC_PROBE
    assert observation.artifact_sha256 == validation.sha256_hex
    assert observation.score == 1.0
    assert observation.threshold == 1.0
    assert observation.passed
    assert observation.evidence_reference == validation.validation_id
    assert observation.provenance_reference == "probe:ffprobe-json-v1"
    assert observation.repair_target is None


def test_failed_technical_validation_requests_only_bounded_technical_repair() -> None:
    observation = technical_observation_from_assembled_validation(
        _technical_validation(passed=False),
        observer_id="technical-observer",
        producer_id="video-producer",
    )
    assert not observation.passed
    assert observation.score == 0.0
    assert observation.repair_target == "artifact:assembled-artifact-001:technical"


def test_thumbnail_generation_rejects_source_artifact_substitution() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        renderer = _WritingRenderer()
        request = _request("b" * 64)
        with pytest.raises(ThumbnailGenerationError, match="SHA-256 mismatch"):
            ThumbnailGenerationCoordinator(renderer).generate(
                request,
                source_path=source,
                source_byte_length=len(body),
                output_directory=root / "thumbnails",
                provenance_reference="assembly:artifact-001",
            )
        assert renderer.calls == 0
        assert source_sha != request.artifact_sha256


def test_thumbnail_generation_rejects_source_length_substitution() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        renderer = _WritingRenderer()
        with pytest.raises(ThumbnailGenerationError, match="byte length mismatch"):
            ThumbnailGenerationCoordinator(renderer).generate(
                _request(source_sha),
                source_path=source,
                source_byte_length=len(body) + 1,
                output_directory=root / "thumbnails",
                provenance_reference="assembly:artifact-001",
            )
        assert renderer.calls == 0


def test_thumbnail_generation_emits_content_addressed_evidence() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        renderer = _WritingRenderer()
        coordinator = ThumbnailGenerationCoordinator(renderer)
        artifact = coordinator.generate(
            _request(source_sha, safe_text="ILAIOS"),
            source_path=source,
            source_byte_length=len(body),
            output_directory=root / "thumbnails",
            provenance_reference="assembly:artifact-001",
        )
        output = Path(artifact.output_path)
        assert output.is_file()
        assert artifact.source_artifact_sha256 == source_sha
        assert artifact.sha256_hex == sha256(output.read_bytes()).hexdigest()
        assert artifact.byte_length == output.stat().st_size
        assert artifact.safe_text_rendered
        assert artifact.renderer_id == renderer.renderer_id
        assert artifact.provenance_reference == "assembly:artifact-001"


def test_thumbnail_generation_fails_if_renderer_emits_no_artifact() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        with pytest.raises(ThumbnailGenerationError, match="did not emit"):
            ThumbnailGenerationCoordinator(_NoOutputRenderer()).generate(
                _request(source_sha),
                source_path=source,
                source_byte_length=len(body),
                output_directory=root / "thumbnails",
                provenance_reference="assembly:artifact-001",
            )


def test_frame_only_renderer_refuses_unmaterialized_safe_text() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        renderer = _WritingRenderer(renders_text=False)
        with pytest.raises(ThumbnailGenerationError, match="cannot materialize"):
            ThumbnailGenerationCoordinator(renderer).generate(
                _request(source_sha, safe_text="must-render"),
                source_path=source,
                source_byte_length=len(body),
                output_directory=root / "thumbnails",
                provenance_reference="assembly:artifact-001",
            )
        assert renderer.calls == 0


def test_ffmpeg_renderer_builds_bounded_frame_extraction_command() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, _, _ = _source(root)
        runner = _RecordingRunner()
        output = root / "thumbnail.jpg"
        FfmpegThumbnailRenderer(runner=runner).render(
            source_path=source,
            output_path=output,
            timestamp_ms=1250,
            width=1280,
            height=720,
            safe_text="",
        )
        command = runner.calls[0]
        assert command[0] == "ffmpeg"
        assert command[command.index("-ss") + 1] == "1.25"
        assert command[command.index("-frames:v") + 1] == "1"
        filter_graph = command[command.index("-vf") + 1]
        assert "scale=1280:720" in filter_graph
        assert "crop=1280:720" in filter_graph


def test_ffmpeg_text_uses_textfile_instead_of_interpolating_user_text() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, _, _ = _source(root)
        font = root / "font.ttf"
        font.write_bytes(b"test-font")
        runner = _RecordingRunner()
        output = root / "thumbnail.jpg"
        safe_text = "A:B, 100% 'safe'"
        FfmpegThumbnailRenderer(runner=runner, font_path=font).render(
            source_path=source,
            output_path=output,
            timestamp_ms=0,
            width=1280,
            height=720,
            safe_text=safe_text,
        )
        command = runner.calls[0]
        assert safe_text not in command
        filter_graph = command[command.index("-vf") + 1]
        assert "drawtext=" in filter_graph
        assert "textfile=" in filter_graph
        assert not output.with_suffix(output.suffix + ".text.txt").exists()


def test_governed_thumbnail_generation_requires_media_write_authority() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source, body, source_sha = _source(root)
        registry = SkillRegistry()
        approve_video_skills(registry)
        renderer = _WritingRenderer()
        executor = GovernedThumbnailExecutor(
            registry,
            AgentProfile("thumbnail-worker", frozenset({"media.read"})),
            ThumbnailGenerationCoordinator(renderer),
        )
        with pytest.raises(RuntimeError, match="expand agent authority"):
            executor.generate(
                _request(source_sha),
                source_path=source,
                source_byte_length=len(body),
                output_directory=root / "thumbnails",
                provenance_reference="assembly:artifact-001",
            )
        assert renderer.calls == 0


def test_real_ffmpeg_thumbnail_generation_produces_requested_dimensions() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe unavailable")

    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = root / "source.mp4"
        subprocess.run(
            (
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=160x90:d=1",
                "-pix_fmt",
                "yuv420p",
                source.as_posix(),
            ),
            check=True,
        )
        body = source.read_bytes()
        source_sha = sha256(body).hexdigest()
        artifact = ThumbnailGenerationCoordinator(FfmpegThumbnailRenderer()).generate(
            _request(source_sha),
            source_path=source,
            source_byte_length=len(body),
            output_directory=root / "thumbnails",
            provenance_reference="test:real-ffmpeg-artifact",
        )
        probe = subprocess.run(
            (
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                artifact.output_path,
            ),
            check=True,
            capture_output=True,
            text=True,
        )
        assert probe.stdout.strip() == "120x120"
