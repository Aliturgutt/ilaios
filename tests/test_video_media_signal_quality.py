from __future__ import annotations

import shutil
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.ffmpeg_media_engine import MediaCommandResult, MediaProbe
from src.video_automation.media_signal_quality import (
    AudioSignalPolicy,
    FfmpegMediaSignalQualityProbe,
    MediaSignalQualityError,
    VisualSignalPolicy,
    signal_quality_observations,
)
from src.video_automation.video_quality import QaObservationSource
from src.video_automation.video_skills import QaDomain


class _Probe:
    def __init__(
        self,
        *,
        duration_seconds: float = 10.0,
        include_audio: bool = True,
    ) -> None:
        self.duration_seconds = duration_seconds
        self.include_audio = include_audio

    def probe(self, path: str | Path) -> MediaProbe:
        streams: list[dict[str, object]] = [
            {"codec_type": "video", "codec_name": "h264"}
        ]
        if self.include_audio:
            streams.append({"codec_type": "audio", "codec_name": "aac"})
        return MediaProbe(
            path=str(Path(path).resolve()),
            format_name="mp4",
            duration_seconds=self.duration_seconds,
            streams=tuple(streams),
        )


class _SignalRunner:
    def __init__(self, *, visual_log: str, audio_log: str) -> None:
        self.visual_log = visual_log
        self.audio_log = audio_log
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> MediaCommandResult:
        assert timeout_seconds > 0
        self.calls.append(argv)
        log = self.visual_log if "-vf" in argv else self.audio_log
        return MediaCommandResult(
            argv=argv,
            return_code=0,
            stdout="",
            stderr=log,
        )


def _source(tmp_path: Path) -> tuple[Path, bytes, str]:
    body = b"media-signal-artifact"
    path = tmp_path / "source.mp4"
    path.write_bytes(body)
    return path, body, sha256(body).hexdigest()


def test_signal_probe_binds_metrics_to_exact_artifact(tmp_path: Path) -> None:
    source, body, source_sha = _source(tmp_path)
    runner = _SignalRunner(
        visual_log=(
            "black_start:0 black_end:1 black_duration:1\n"
            "freeze_start:2 freeze_end:2.5 freeze_duration: 0.5"
        ),
        audio_log="silence_start:0 silence_end:0.5 | silence_duration: 0.5",
    )
    evidence = FfmpegMediaSignalQualityProbe(
        visual_policy=VisualSignalPolicy(
            max_black_fraction=0.20,
            max_freeze_seconds=1.0,
        ),
        audio_policy=AudioSignalPolicy(max_silence_fraction=0.20),
        media_probe=_Probe(duration_seconds=10.0),
        runner=runner,
    ).probe(
        source,
        artifact_sha256=source_sha,
        byte_length=len(body),
    )
    assert len(runner.calls) == 2
    assert evidence.artifact_sha256 == source_sha
    assert evidence.black_fraction == pytest.approx(0.1)
    assert evidence.max_freeze_seconds == pytest.approx(0.5)
    assert evidence.silence_fraction == pytest.approx(0.05)
    assert evidence.visual_passed
    assert evidence.audio_passed


def test_signal_probe_fails_domains_when_explicit_policy_is_exceeded(
    tmp_path: Path,
) -> None:
    source, body, source_sha = _source(tmp_path)
    evidence = FfmpegMediaSignalQualityProbe(
        visual_policy=VisualSignalPolicy(
            max_black_fraction=0.20,
            max_freeze_seconds=1.0,
        ),
        audio_policy=AudioSignalPolicy(max_silence_fraction=0.20),
        media_probe=_Probe(duration_seconds=10.0),
        runner=_SignalRunner(
            visual_log=(
                "black_start:0 black_end:3 black_duration:3\n"
                "freeze_start:4 freeze_end:6 freeze_duration: 2"
            ),
            audio_log="silence_start:0 silence_end:4 | silence_duration: 4",
        ),
    ).probe(
        source,
        artifact_sha256=source_sha,
        byte_length=len(body),
    )
    assert not evidence.visual_passed
    assert not evidence.audio_passed
    visual, audio = signal_quality_observations(
        evidence,
        observer_id="signal-observer",
        producer_id="video-producer",
    )
    assert visual.domain is QaDomain.VISUAL
    assert audio.domain is QaDomain.AUDIO
    assert visual.source is QaObservationSource.DETERMINISTIC_PROBE
    assert audio.source is QaObservationSource.DETERMINISTIC_PROBE
    assert not visual.passed and visual.repair_target is not None
    assert not audio.passed and audio.repair_target is not None


def test_signal_probe_rejects_sha_substitution_before_ffmpeg(tmp_path: Path) -> None:
    source, body, _ = _source(tmp_path)
    runner = _SignalRunner(visual_log="", audio_log="")
    with pytest.raises(MediaSignalQualityError, match="SHA-256 mismatch"):
        FfmpegMediaSignalQualityProbe(
            media_probe=_Probe(),
            runner=runner,
        ).probe(
            source,
            artifact_sha256="b" * 64,
            byte_length=len(body),
        )
    assert runner.calls == []


def test_signal_probe_rejects_missing_audio_stream_before_ffmpeg(
    tmp_path: Path,
) -> None:
    source, body, source_sha = _source(tmp_path)
    runner = _SignalRunner(visual_log="", audio_log="")
    with pytest.raises(MediaSignalQualityError, match="requires an audio stream"):
        FfmpegMediaSignalQualityProbe(
            media_probe=_Probe(include_audio=False),
            runner=runner,
        ).probe(
            source,
            artifact_sha256=source_sha,
            byte_length=len(body),
        )
    assert runner.calls == []


def test_signal_observations_remain_independent_from_artifact_producer(
    tmp_path: Path,
) -> None:
    source, body, source_sha = _source(tmp_path)
    evidence = FfmpegMediaSignalQualityProbe(
        media_probe=_Probe(),
        runner=_SignalRunner(visual_log="", audio_log=""),
    ).probe(
        source,
        artifact_sha256=source_sha,
        byte_length=len(body),
    )
    with pytest.raises(ValueError, match="independent from artifact producer"):
        signal_quality_observations(
            evidence,
            observer_id="same-service",
            producer_id="same-service",
        )


def test_real_ffmpeg_signal_probe_accepts_active_video_and_audio(
    tmp_path: Path,
) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe unavailable")

    source = tmp_path / "active.mp4"
    subprocess.run(
        (
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ),
        check=True,
        capture_output=True,
        timeout=30,
    )
    body = source.read_bytes()
    evidence = FfmpegMediaSignalQualityProbe(
        visual_policy=VisualSignalPolicy(
            max_black_fraction=0.05,
            max_freeze_seconds=0.5,
        ),
        audio_policy=AudioSignalPolicy(max_silence_fraction=0.05),
    ).probe(
        source,
        artifact_sha256=sha256(body).hexdigest(),
        byte_length=len(body),
    )
    assert evidence.visual_passed
    assert evidence.audio_passed
    assert evidence.black_fraction <= 0.05
    assert evidence.silence_fraction <= 0.05
