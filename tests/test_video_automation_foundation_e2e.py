"""Foundation local/free integration gate for ILAIOS Video Automation.

This test proves that existing canonical components can produce and independently
probe a real local MP4 without paid providers or network access.

It intentionally adds no new production orchestration. M30 owns the final
runtime entrypoint and top-level workflow coordination.
"""

from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

from src.video_automation.ffmpeg_media_engine import FfmpegMediaEngine
from src.video_automation.models import (
    MediaAsset,
    MediaType,
    Timeline,
    TimelineItem,
)
from src.video_automation.remotion_composition import (
    RemotionCompositionAdapter,
    RemotionCompositionElement,
)
from src.video_automation.render_engine import (
    LocalFfmpegRenderExecutor,
    RenderEngine,
)


def _run_ffmpeg(*arguments: str) -> None:
    completed = subprocess.run(
        ("ffmpeg", "-y", "-v", "error", *arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=60.0,
    )

    if completed.returncode != 0:
        raise AssertionError(
            "FFmpeg fixture generation failed:\n"
            + completed.stderr
        )


def test_foundation_local_free_pipeline_produces_real_render(
    tmp_path: Path,
) -> None:
    job_id = "foundation-e2e-job"
    source_path = tmp_path / "source.mp4"

    _run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=160x284:r=30:d=1",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        "1",
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(source_path),
    )

    source_bytes = source_path.read_bytes()

    assert source_bytes

    asset = MediaAsset(
        asset_id="foundation-video-asset",
        job_id=job_id,
        media_type=MediaType.VIDEO,
        file_path=str(source_path.resolve()),
        checksum_sha256=sha256(source_bytes).hexdigest(),
        provider_name="local-test",
        source_reference="local://source.mp4",
        validated=True,
    )

    timeline = Timeline(
        job_id=job_id,
        items=(
            TimelineItem(
                item_id="foundation-timeline-item",
                asset_id=asset.asset_id,
                start_seconds=0.0,
                duration_seconds=1.0,
                layer=0,
            ),
        ),
    )

    composition = RemotionCompositionAdapter().prepare(
        job_id=job_id,
        timeline=timeline,
        assets=(asset,),
        elements=(
            RemotionCompositionElement(
                element_id="foundation-title",
                kind="title",
                start_seconds=0.0,
                duration_seconds=1.0,
                layer=1,
                payload={
                    "text": "Hermes Foundation E2E",
                },
            ),
        ),
        output_directory=tmp_path / "composition",
        duration_seconds=1.0,
        fps=30,
        width=160,
        height=284,
    )

    probe_engine = FfmpegMediaEngine(
        timeout_seconds=60.0,
    )

    artifact = RenderEngine(
        executor=LocalFfmpegRenderExecutor(
            timeout_seconds=60.0,
        ),
        probe_engine=probe_engine,
    ).render(
        job_id=job_id,
        composition=composition,
        output_path=tmp_path / "final.mp4",
    )

    final_path = Path(artifact.file_path)

    assert final_path.is_file()
    assert final_path.stat().st_size > 0
    assert artifact.job_id == job_id
    assert artifact.codec == "h264"
    assert artifact.audio_codec == "aac"
    assert artifact.resolution == "160x284"
    assert artifact.aspect_ratio == "40:71"
    assert artifact.fps == 30.0
    assert artifact.checksum_sha256 == sha256(
        final_path.read_bytes()
    ).hexdigest()
    assert artifact.size_bytes == final_path.stat().st_size

    independent_probe = probe_engine.probe(
        final_path
    )

    video_streams = tuple(
        stream
        for stream in independent_probe.streams
        if stream.get("codec_type") == "video"
    )
    audio_streams = tuple(
        stream
        for stream in independent_probe.streams
        if stream.get("codec_type") == "audio"
    )

    assert len(video_streams) == 1
    assert len(audio_streams) == 1
    assert video_streams[0]["codec_name"] == "h264"
    assert audio_streams[0]["codec_name"] == "aac"
    assert video_streams[0]["width"] == 160
    assert video_streams[0]["height"] == 284
    assert independent_probe.duration_seconds > 0
