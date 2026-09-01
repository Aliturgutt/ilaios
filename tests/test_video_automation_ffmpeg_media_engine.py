"""Tests for canonical M18 general FFmpeg media engine."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.ffmpeg_media_engine import (
    FfmpegMediaEngine,
    FfmpegMediaEngineError,
    MediaCommandResult,
    MediaProbe,
)


class _RecordingRunner:
    def __init__(
        self,
        *,
        stdout: str = "",
    ) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.stdout = stdout

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> MediaCommandResult:
        assert timeout_seconds > 0

        self.calls.append(argv)

        return MediaCommandResult(
            argv=argv,
            return_code=0,
            stdout=self.stdout,
            stderr="",
        )


def _file(
    root: Path,
    name: str,
) -> Path:
    path = root / name
    path.write_bytes(b"media")
    return path


def test_probe_normalizes_ffprobe_json() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mp4")

        payload = {
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "4.250000",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                }
            ],
        }

        runner = _RecordingRunner(stdout=json.dumps(payload))

        engine = FfmpegMediaEngine(
            runner=runner,
        )

        probe = engine.probe(source)

        assert isinstance(probe, MediaProbe)
        assert probe.duration_seconds == 4.25
        assert probe.path == str(source.resolve())
        assert len(probe.streams) == 1
        assert runner.calls[0][0] == "ffprobe"


def test_trim_builds_expected_command() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mp4")
        output = root / "out.mp4"

        runner = _RecordingRunner()

        engine = FfmpegMediaEngine(
            runner=runner,
        )

        result = engine.trim(
            input_path=source,
            output_path=output,
            start_seconds=1.5,
            duration_seconds=3.0,
        )

        assert result.return_code == 0

        assert runner.calls == [
            (
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                "1.5",
                "-i",
                str(source),
                "-t",
                "3",
                "-c",
                "copy",
                str(output),
            )
        ]


def test_transcode_builds_codec_conversion_command() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mov")
        output = root / "output.mp4"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).transcode(
            input_path=source,
            output_path=output,
            video_codec="libx264",
            audio_codec="aac",
        )

        command = runner.calls[0]

        assert "-c:v" in command
        assert "libx264" in command
        assert "-c:a" in command
        assert "aac" in command


def test_video_normalization_builds_scale_crop_fps_filter() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mp4")
        output = root / "normalized.mp4"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).normalize_video(
            input_path=source,
            output_path=output,
            width=720,
            height=1280,
            fps=30,
            video_codec="libx264",
            audio_codec="aac",
        )

        command = runner.calls[0]

        filter_value = command[command.index("-vf") + 1]

        assert "scale=720:1280" in filter_value
        assert "crop=720:1280" in filter_value
        assert "fps=30" in filter_value


def test_audio_normalization_uses_loudnorm() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "voice.wav")
        output = root / "normalized.wav"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).normalize_audio(
            input_path=source,
            output_path=output,
            target_lufs=-16.0,
        )

        command = runner.calls[0]

        assert "-af" in command

        filter_value = command[command.index("-af") + 1]

        assert filter_value == "loudnorm=I=-16:TP=-1.5:LRA=11"


def test_crop_builds_bounded_video_filter() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mp4")
        runner = _RecordingRunner()
        FfmpegMediaEngine(runner=runner).crop(
            input_path=source,
            output_path=root / "crop.mp4",
            width=100,
            height=200,
            x=3,
            y=4,
        )
        command = runner.calls[0]
        assert command[command.index("-vf") + 1] == "crop=100:200:3:4"


def test_audio_mix_requires_multiple_inputs() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "voice.wav")

        with pytest.raises(
            FfmpegMediaEngineError,
            match="at least two",
        ):
            FfmpegMediaEngine(
                runner=_RecordingRunner(),
            ).mix_audio(
                input_paths=(source,),
                output_path=root / "mix.wav",
            )


def test_audio_mix_builds_amix_command() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice = _file(root, "voice.wav")
        music = _file(root, "music.wav")
        output = root / "mix.wav"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).mix_audio(
            input_paths=(voice, music),
            output_path=output,
        )

        command = runner.calls[0]

        assert command.count("-i") == 2
        assert "-filter_complex" in command

        filter_value = command[command.index("-filter_complex") + 1]

        assert filter_value == "amix=inputs=2:duration=longest:normalize=0"


def test_mux_maps_video_and_audio_streams() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        video = _file(root, "video.mp4")
        audio = _file(root, "audio.wav")
        output = root / "muxed.mp4"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).mux(
            video_path=video,
            audio_path=audio,
            output_path=output,
        )

        command = runner.calls[0]

        assert "0:v:0" in command
        assert "1:a:0" in command
        assert "-shortest" in command


def test_overlay_builds_bounded_filter_command() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "video.mp4")
        overlay = _file(root, "overlay.png")
        output = root / "composited.mp4"
        runner = _RecordingRunner()
        FfmpegMediaEngine(runner=runner).overlay(
            input_path=source,
            overlay_path=overlay,
            output_path=output,
            x=12,
            y=-4,
        )
        command = runner.calls[0]
        assert command.count("-i") == 2
        assert command[command.index("-filter_complex") + 1] == (
            "[0:v][1:v]overlay=x=12:y=-4:format=auto"
        )


def test_concatenate_executes_concat_demuxer() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        first = _file(root, "first.mp4")
        second = _file(root, "second.mp4")
        output = root / "joined.mp4"

        runner = _RecordingRunner()

        FfmpegMediaEngine(
            runner=runner,
        ).concatenate(
            input_paths=(first, second),
            output_path=output,
        )

        command = runner.calls[0]

        assert "-f" in command
        assert "concat" in command
        assert "-safe" in command
        assert "0" in command

        manifest = output.with_suffix(output.suffix + ".m18-concat.txt")

        assert not manifest.exists()


def test_missing_input_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        with pytest.raises(
            FfmpegMediaEngineError,
            match="does not exist",
        ):
            FfmpegMediaEngine(
                runner=_RecordingRunner(),
            ).trim(
                input_path=root / "missing.mp4",
                output_path=root / "output.mp4",
                start_seconds=0.0,
                duration_seconds=1.0,
            )


def test_negative_trim_start_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)
        source = _file(root, "input.mp4")

        with pytest.raises(
            FfmpegMediaEngineError,
            match="start_seconds",
        ):
            FfmpegMediaEngine(
                runner=_RecordingRunner(),
            ).trim(
                input_path=source,
                output_path=root / "output.mp4",
                start_seconds=-1.0,
                duration_seconds=1.0,
            )


def test_non_positive_timeout_fails_closed() -> None:
    with pytest.raises(
        FfmpegMediaEngineError,
        match="timeout_seconds",
    ):
        FfmpegMediaEngine(
            timeout_seconds=0,
        )
