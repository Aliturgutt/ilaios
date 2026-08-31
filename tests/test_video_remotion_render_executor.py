from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.ffmpeg_media_engine import (
    FfmpegMediaEngine,
    MediaCommandResult,
    SubprocessCommandRunner,
)
from src.video_automation.remotion_composition import RemotionCompositionArtifact
from src.video_automation.remotion_render_executor import RemotionCliRenderExecutor
from src.video_automation.render_engine import (
    RenderEngine,
    RenderEngineError,
    RenderExecutionRequest,
)


class _CreatingRunner:
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
        Path(argv[-1]).write_bytes(b"rendered")
        return MediaCommandResult(argv=argv, return_code=0, stdout="", stderr="")


def _composition(tmp_path: Path) -> RemotionCompositionArtifact:
    manifest = tmp_path / "composition.json"
    entry = tmp_path / "composition.tsx"
    payload = {
        "schema_version": 1,
        "engine": "remotion",
        "job_id": "job-remotion",
        "composition": {
            "duration_seconds": 1.0,
            "duration_frames": 12,
            "fps": 12,
            "width": 320,
            "height": 180,
        },
        "timeline": [],
        "elements": [
            {
                "element_id": "title-1",
                "kind": "title",
                "start_seconds": 0.0,
                "duration_seconds": 1.0,
                "start_frame": 0,
                "duration_frames": 12,
                "layer": 1,
                "payload": {"text": "ILAIOS"},
            },
            {
                "element_id": "progress-1",
                "kind": "progress_indicator",
                "start_seconds": 0.0,
                "duration_seconds": 1.0,
                "start_frame": 0,
                "duration_frames": 12,
                "layer": 2,
                "payload": {"label": "progress"},
            },
        ],
    }
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    entry.write_text("export const ilaiosComposition = {};\n", encoding="utf-8")
    return RemotionCompositionArtifact(
        composition_id="remotion-composition-test",
        job_id="job-remotion",
        manifest_path=str(manifest),
        manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
        entry_source_path=str(entry),
        entry_source_sha256=sha256(entry.read_bytes()).hexdigest(),
        duration_seconds=1.0,
        fps=12,
        width=320,
        height=180,
    )


def test_remotion_executor_uses_repo_runtime_then_canonical_audio_mux(tmp_path: Path) -> None:
    runtime = tmp_path / "render.mjs"
    runtime.write_text("// test runtime\n", encoding="utf-8")
    runner = _CreatingRunner()
    composition = _composition(tmp_path)
    output = tmp_path / "final.mp4"

    result = RemotionCliRenderExecutor(
        runtime_script=runtime,
        runner=runner,
        timeout_seconds=30,
    ).execute(
        RenderExecutionRequest(
            job_id=composition.job_id,
            composition=composition,
            output_path=str(output),
        )
    )

    assert result.output_path == str(output.resolve())
    assert result.renderer_id == "remotion-renderer-4.0.518-v1"
    assert output.read_bytes() == b"rendered"
    assert len(runner.calls) == 2
    assert runner.calls[0][:2] == ("node", str(runtime.resolve()))
    assert runner.calls[0][2] == str(Path(composition.manifest_path).resolve())
    assert runner.calls[1][0] == "ffmpeg"
    assert "anullsrc=channel_layout=stereo:sample_rate=48000" in runner.calls[1]
    assert not output.with_suffix(".mp4.remotion-video.mp4").exists()


def test_remotion_executor_fails_closed_without_runtime(tmp_path: Path) -> None:
    composition = _composition(tmp_path)
    request = RenderExecutionRequest(
        job_id=composition.job_id,
        composition=composition,
        output_path=str(tmp_path / "final.mp4"),
    )

    with pytest.raises(RenderEngineError, match="runtime is unavailable"):
        RemotionCliRenderExecutor(
            runtime_script=tmp_path / "missing.mjs",
            runner=_CreatingRunner(),
        ).execute(request)


def test_real_remotion_executor_renders_changing_pixels_and_audio(tmp_path: Path) -> None:
    if os.getenv("ILAIOS_RUN_REMOTION_E2E") != "1":
        pytest.skip("real Remotion E2E is enabled only by the dedicated CI gate")

    composition = _composition(tmp_path)
    runner = SubprocessCommandRunner()
    media_engine = FfmpegMediaEngine(runner=runner, timeout_seconds=120)
    output = tmp_path / "real-remotion.mp4"

    artifact = RenderEngine(
        executor=RemotionCliRenderExecutor(runner=runner, timeout_seconds=120),
        probe_engine=media_engine,
    ).render(
        job_id=composition.job_id,
        composition=composition,
        output_path=output,
    )

    assert artifact.size_bytes > 0
    assert artifact.codec == "h264"
    assert artifact.audio_codec == "aac"
    assert artifact.resolution == "320x180"

    frames = runner.run(
        (
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(output),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ),
        timeout_seconds=120,
    ).stdout
    hashes = {
        line.rsplit(",", 1)[-1].strip()
        for line in frames.splitlines()
        if line and not line.startswith("#") and "," in line
    }
    assert len(hashes) > 1, "pixel-level evidence requires changing rendered frames"
