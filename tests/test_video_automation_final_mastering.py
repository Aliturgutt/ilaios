from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from src.video_automation.ffmpeg_media_engine import MediaCommandResult, MediaProbe
from src.video_automation.final_mastering import Final1080pMasterer, FinalMasteringError


class FakeEngine:
    def __init__(self, probes: Mapping[str, tuple[int, int]]) -> None:
        self._probes = dict(probes)
        self.normalize_calls: list[tuple[int, int]] = []

    def probe(self, path: str | Path) -> MediaProbe:
        resolved = str(Path(path).resolve())
        width, height = self._probes[resolved]
        return MediaProbe(
            path=resolved,
            format_name="mp4",
            duration_seconds=1.0,
            streams=({"codec_type": "video", "width": width, "height": height},),
        )

    def normalize_video(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        width: int,
        height: int,
        fps: int,
        video_codec: str,
        audio_codec: str,
    ) -> MediaCommandResult:
        assert fps == 30
        assert video_codec == "libx264"
        assert audio_codec == "aac"
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"1080p-master")
        self._probes[str(output.resolve())] = (width, height)
        self.normalize_calls.append((width, height))
        return MediaCommandResult(argv=("ffmpeg",), return_code=0, stdout="", stderr="")


def test_landscape_720p_is_mastered_to_1080p(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "master.mp4"
    engine = FakeEngine({str(source.resolve()): (1280, 720)})

    receipt = Final1080pMasterer(engine).master(input_path=source, output_path=output)

    assert receipt.upgraded is True
    assert (receipt.output_width, receipt.output_height) == (1920, 1080)
    assert receipt.provider_cost_usd == 0.0
    assert engine.normalize_calls == [(1920, 1080)]


def test_portrait_720p_is_mastered_to_vertical_1080p(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "master.mp4"
    engine = FakeEngine({str(source.resolve()): (720, 1280)})

    receipt = Final1080pMasterer(engine).master(input_path=source, output_path=output)

    assert (receipt.output_width, receipt.output_height) == (1080, 1920)
    assert engine.normalize_calls == [(1080, 1920)]


def test_square_480p_is_mastered_to_square_1080p(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "master.mp4"
    engine = FakeEngine({str(source.resolve()): (480, 480)})

    receipt = Final1080pMasterer(engine).master(input_path=source, output_path=output)

    assert (receipt.output_width, receipt.output_height) == (1080, 1080)
    assert engine.normalize_calls == [(1080, 1080)]


def test_existing_1080p_is_not_reencoded(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"already-mastered")
    engine = FakeEngine({str(source.resolve()): (1920, 1080)})

    receipt = Final1080pMasterer(engine).master(
        input_path=source,
        output_path=tmp_path / "unused.mp4",
    )

    assert receipt.upgraded is False
    assert receipt.output_path == str(source.resolve())
    assert engine.normalize_calls == []


def test_4k_is_preserved_without_reencode(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"4k")
    engine = FakeEngine({str(source.resolve()): (3840, 2160)})

    receipt = Final1080pMasterer(engine).master(
        input_path=source,
        output_path=tmp_path / "unused.mp4",
    )

    assert receipt.upgraded is False
    assert (receipt.output_width, receipt.output_height) == (3840, 2160)
    assert engine.normalize_calls == []


def test_noncanonical_shape_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    engine = FakeEngine({str(source.resolve()): (640, 480)})

    with pytest.raises(FinalMasteringError, match="unsupported final-master aspect ratio"):
        Final1080pMasterer(engine).master(
            input_path=source,
            output_path=tmp_path / "master.mp4",
        )


def test_upscale_never_overwrites_source(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    engine = FakeEngine({str(source.resolve()): (1280, 720)})

    with pytest.raises(FinalMasteringError, match="must not overwrite source"):
        Final1080pMasterer(engine).master(input_path=source, output_path=source)
