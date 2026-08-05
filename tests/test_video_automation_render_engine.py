"""Tests for canonical M20 Render Engine."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.ffmpeg_media_engine import (
    MediaCommandResult,
    MediaProbe,
)
from src.video_automation.models import RenderArtifact
from src.video_automation.remotion_composition import (
    RemotionCompositionArtifact,
)
from src.video_automation.render_engine import (
    LocalFfmpegRenderExecutor,
    RenderEngine,
    RenderEngineError,
    RenderExecutionRequest,
    RenderExecutionResult,
)


def _composition(
    root: Path,
    *,
    job_id: str = "job-1",
) -> RemotionCompositionArtifact:
    manifest = root / "composition.json"
    entry = root / "composition.tsx"

    manifest.write_text(
        """{
  "schema_version": 1,
  "engine": "remotion",
  "job_id": "job-1",
  "composition": {
    "duration_seconds": 5.0,
    "duration_frames": 150,
    "fps": 30,
    "width": 720,
    "height": 1280
  },
  "timeline": [],
  "elements": []
}
""",
        encoding="utf-8",
    )

    entry.write_text(
        "export const composition = {};\n",
        encoding="utf-8",
    )

    return RemotionCompositionArtifact(
        composition_id="remotion-composition-test",
        job_id=job_id,
        manifest_path=str(manifest.resolve()),
        manifest_sha256=sha256(
            manifest.read_bytes()
        ).hexdigest(),
        entry_source_path=str(entry.resolve()),
        entry_source_sha256=sha256(
            entry.read_bytes()
        ).hexdigest(),
        duration_seconds=5.0,
        fps=30,
        width=720,
        height=1280,
    )


class _FakeExecutor:
    def __init__(
        self,
        *,
        payload: bytes = b"rendered-media",
        renderer_id: str = "fake-remotion-renderer",
    ) -> None:
        self.payload = payload
        self.renderer_id = renderer_id
        self.requests: list[
            RenderExecutionRequest
        ] = []

    def execute(
        self,
        request: RenderExecutionRequest,
    ) -> RenderExecutionResult:
        self.requests.append(
            request
        )

        path = Path(
            request.output_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            self.payload
        )

        return RenderExecutionResult(
            output_path=str(path),
            renderer_id=self.renderer_id,
        )


class _FakeProbeEngine:
    def __init__(
        self,
        *,
        duration_seconds: float = 5.0,
        width: int = 720,
        height: int = 1280,
        fps: str = "30/1",
        video_codec: str = "h264",
        audio_codec: str = "aac",
    ) -> None:
        self.duration_seconds = duration_seconds
        self.width = width
        self.height = height
        self.fps = fps
        self.video_codec = video_codec
        self.audio_codec = audio_codec

    def probe(
        self,
        path: str | Path,
    ) -> MediaProbe:
        return MediaProbe(
            path=str(
                Path(path).resolve()
            ),
            format_name="mov,mp4,m4a,3gp,3g2,mj2",
            duration_seconds=self.duration_seconds,
            streams=(
                {
                    "codec_type": "video",
                    "codec_name": self.video_codec,
                    "width": self.width,
                    "height": self.height,
                    "avg_frame_rate": self.fps,
                },
                {
                    "codec_type": "audio",
                    "codec_name": self.audio_codec,
                },
            ),
        )


def test_render_creates_existing_canonical_render_artifact() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        composition = _composition(
            root
        )

        executor = _FakeExecutor()

        engine = RenderEngine(
            executor=executor,
            probe_engine=_FakeProbeEngine(),
        )

        artifact = engine.render(
            job_id="job-1",
            composition=composition,
            output_path=root / "final.mp4",
        )

        assert isinstance(
            artifact,
            RenderArtifact,
        )

        assert artifact.job_id == "job-1"
        assert artifact.codec == "h264"
        assert artifact.audio_codec == "aac"
        assert artifact.resolution == "720x1280"
        assert artifact.duration_seconds == 5.0
        assert artifact.fps == 30.0
        assert artifact.aspect_ratio == "9:16"

        output = Path(
            artifact.file_path
        )

        assert output.is_file()

        assert artifact.size_bytes == len(
            b"rendered-media"
        )

        assert (
            artifact.checksum_sha256
            == sha256(
                output.read_bytes()
            ).hexdigest()
        )


def test_render_request_contains_m19_composition() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        composition = _composition(
            root
        )

        executor = _FakeExecutor()

        RenderEngine(
            executor=executor,
            probe_engine=_FakeProbeEngine(),
        ).render(
            job_id="job-1",
            composition=composition,
            output_path=root / "final.mp4",
        )

        assert len(
            executor.requests
        ) == 1

        request = executor.requests[0]

        assert (
            request.composition
            == composition
        )

        assert request.job_id == "job-1"


def test_artifact_identity_is_deterministic() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        composition = _composition(
            root
        )

        first = RenderEngine(
            executor=_FakeExecutor(),
            probe_engine=_FakeProbeEngine(),
        ).render(
            job_id="job-1",
            composition=composition,
            output_path=root / "first.mp4",
        )

        second = RenderEngine(
            executor=_FakeExecutor(),
            probe_engine=_FakeProbeEngine(),
        ).render(
            job_id="job-1",
            composition=composition,
            output_path=root / "second.mp4",
        )

        assert (
            first.artifact_id
            == second.artifact_id
        )

        assert (
            first.checksum_sha256
            == second.checksum_sha256
        )


def test_fractional_frame_rate_is_normalized() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        artifact = RenderEngine(
            executor=_FakeExecutor(),
            probe_engine=_FakeProbeEngine(
                fps="30000/1001",
            ),
        ).render(
            job_id="job-1",
            composition=_composition(root),
            output_path=root / "final.mp4",
        )

        assert artifact.fps == pytest.approx(
            29.97002997
        )


def test_composition_checksum_mutation_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        composition = _composition(
            root
        )

        Path(
            composition.manifest_path
        ).write_text(
            '{"changed":true}\n',
            encoding="utf-8",
        )

        with pytest.raises(
            RenderEngineError,
            match="manifest checksum changed",
        ):
            RenderEngine(
                executor=_FakeExecutor(),
                probe_engine=_FakeProbeEngine(),
            ).render(
                job_id="job-1",
                composition=composition,
                output_path=root / "final.mp4",
            )


def test_composition_job_mismatch_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        composition = _composition(
            root,
            job_id="other-job",
        )

        with pytest.raises(
            RenderEngineError,
            match="job_id",
        ):
            RenderEngine(
                executor=_FakeExecutor(),
                probe_engine=_FakeProbeEngine(),
            ).render(
                job_id="job-1",
                composition=composition,
                output_path=root / "final.mp4",
            )


class _WrongOutputExecutor:
    def execute(
        self,
        request: RenderExecutionRequest,
    ) -> RenderExecutionResult:
        wrong = (
            Path(request.output_path).parent
            / "wrong.mp4"
        )

        wrong.write_bytes(
            b"wrong"
        )

        return RenderExecutionResult(
            output_path=str(wrong),
            renderer_id="wrong-output",
        )


def test_renderer_output_path_mismatch_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        with pytest.raises(
            RenderEngineError,
            match="does not match",
        ):
            RenderEngine(
                executor=_WrongOutputExecutor(),
                probe_engine=_FakeProbeEngine(),
            ).render(
                job_id="job-1",
                composition=_composition(root),
                output_path=root / "final.mp4",
            )


class _EmptyOutputExecutor:
    def execute(
        self,
        request: RenderExecutionRequest,
    ) -> RenderExecutionResult:
        path = Path(
            request.output_path
        )

        path.write_bytes(
            b""
        )

        return RenderExecutionResult(
            output_path=str(path),
            renderer_id="empty-output",
        )


def test_empty_renderer_output_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        with pytest.raises(
            RenderEngineError,
            match="must not be empty",
        ):
            RenderEngine(
                executor=_EmptyOutputExecutor(),
                probe_engine=_FakeProbeEngine(),
            ).render(
                job_id="job-1",
                composition=_composition(root),
                output_path=root / "final.mp4",
            )


def test_missing_audio_stream_fails_closed() -> None:
    class VideoOnlyProbe:
        def probe(
            self,
            path: str | Path,
        ) -> MediaProbe:
            return MediaProbe(
                path=str(path),
                format_name="mp4",
                duration_seconds=5.0,
                streams=(
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 720,
                        "height": 1280,
                        "avg_frame_rate": "30/1",
                    },
                ),
            )

    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        with pytest.raises(
            RenderEngineError,
            match="audio stream",
        ):
            RenderEngine(
                executor=_FakeExecutor(),
                probe_engine=VideoOnlyProbe(),
            ).render(
                job_id="job-1",
                composition=_composition(root),
                output_path=root / "final.mp4",
            )


def test_zero_duration_probe_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        with pytest.raises(
            RenderEngineError,
            match="duration",
        ):
            RenderEngine(
                executor=_FakeExecutor(),
                probe_engine=_FakeProbeEngine(
                    duration_seconds=0.0,
                ),
            ).render(
                job_id="job-1",
                composition=_composition(root),
                output_path=root / "final.mp4",
            )

class _MaterializingRunner:
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

        output_path = Path(argv[-1])
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_path.write_bytes(
            b"local-render-output"
        )

        return MediaCommandResult(
            argv=argv,
            return_code=0,
            stdout="",
            stderr="",
        )


def test_local_ffmpeg_executor_materializes_render_output() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        composition = _composition(root)
        runner = _MaterializingRunner()

        executor = LocalFfmpegRenderExecutor(
            runner=runner,
            timeout_seconds=30.0,
        )

        output_path = root / "local-render.mp4"

        result = executor.execute(
            RenderExecutionRequest(
                job_id="job-1",
                composition=composition,
                output_path=str(output_path),
            )
        )

        assert result.output_path == str(output_path)
        assert (
            result.renderer_id
            == "local-ffmpeg-renderer-v1"
        )
        assert output_path.read_bytes() == (
            b"local-render-output"
        )

        command = runner.calls[0]

        assert command[0] == "ffmpeg"
        assert "color=c=black:s=720x1280:r=30:d=5" in command
        assert (
            "anullsrc=channel_layout=stereo:"
            "sample_rate=48000"
        ) in command
        assert "libx264" in command
        assert "aac" in command
        assert str(output_path) == command[-1]


def test_local_ffmpeg_executor_rejects_manifest_metadata_drift() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        composition = _composition(root)

        manifest_path = Path(
            composition.manifest_path
        )

        manifest_path.write_text(
            """{
  "composition": {
    "duration_seconds": 6.0,
    "fps": 30,
    "width": 720,
    "height": 1280
  }
}
""",
            encoding="utf-8",
        )

        changed_composition = RemotionCompositionArtifact(
            composition_id=composition.composition_id,
            job_id=composition.job_id,
            manifest_path=composition.manifest_path,
            manifest_sha256=sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
            entry_source_path=composition.entry_source_path,
            entry_source_sha256=composition.entry_source_sha256,
            duration_seconds=5.0,
            fps=30,
            width=720,
            height=1280,
        )

        with pytest.raises(
            RenderEngineError,
            match="manifest duration",
        ):
            LocalFfmpegRenderExecutor(
                runner=_MaterializingRunner(),
            ).execute(
                RenderExecutionRequest(
                    job_id="job-1",
                    composition=changed_composition,
                    output_path=str(
                        root / "final.mp4"
                    ),
                )
            )


def test_render_engine_accepts_concrete_local_executor() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        composition = _composition(root)

        artifact = RenderEngine(
            executor=LocalFfmpegRenderExecutor(
                runner=_MaterializingRunner(),
            ),
            probe_engine=_FakeProbeEngine(),
        ).render(
            job_id="job-1",
            composition=composition,
            output_path=root / "final.mp4",
        )

        assert isinstance(
            artifact,
            RenderArtifact,
        )
        assert artifact.job_id == "job-1"
        assert artifact.resolution == "720x1280"
        assert artifact.codec == "h264"
        assert artifact.audio_codec == "aac"
        assert Path(
            artifact.file_path
        ).read_bytes() == b"local-render-output"
