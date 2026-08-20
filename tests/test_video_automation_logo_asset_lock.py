from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from src.video_automation.ffmpeg_media_engine import MediaCommandResult
from src.video_automation.logo_asset_lock import (
    LogoAssetLockCompositor,
    LogoAssetLockError,
    LogoAssetLockInput,
    LogoPlacement,
    resolve_logo_placement,
)


class _Engine:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path, Path, int, int]] = []

    def overlay(
        self,
        *,
        input_path: str | Path,
        overlay_path: str | Path,
        output_path: str | Path,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult:
        source = Path(input_path)
        logo = Path(overlay_path)
        output = Path(output_path)
        assert source.is_file()
        assert logo.is_file()
        output.write_bytes(b"locked-video")
        self.calls.append((source, logo, output, x, y))
        return MediaCommandResult(("ffmpeg",), 0, "", "")


def _logo(*, width: int = 200, height: int = 100, instruction: str | None = None) -> LogoAssetLockInput:
    content = b"canonical-logo-bytes"
    return LogoAssetLockInput(
        content=content,
        mime_type="image/png",
        sha256_hex=sha256(content).hexdigest(),
        width=width,
        height=height,
        instruction=instruction,
    )


def test_logo_asset_lock_uses_exact_admitted_bytes_and_bottom_right_default(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "locked.mp4"
    engine = _Engine()

    result = LogoAssetLockCompositor(engine=engine).apply(
        video_path=source,
        output_path=output,
        logo=_logo(),
        frame_width=1920,
        frame_height=1080,
    )

    assert output.read_bytes() == b"locked-video"
    assert result.placement is LogoPlacement.BOTTOM_RIGHT
    assert result.margin == 27
    assert result.x == 1920 - 200 - 27
    assert result.y == 1080 - 100 - 27
    assert len(engine.calls) == 1
    temporary_logo = engine.calls[0][1]
    assert not temporary_logo.exists()


def test_logo_asset_lock_honors_explicit_turkish_top_left_placement(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "locked.mp4"
    engine = _Engine()

    result = LogoAssetLockCompositor(engine=engine).apply(
        video_path=source,
        output_path=output,
        logo=_logo(instruction="Logoyu sol üst köşede koru"),
        frame_width=1920,
        frame_height=1080,
    )

    assert result.placement is LogoPlacement.TOP_LEFT
    assert result.x == result.margin
    assert result.y == result.margin


def test_logo_asset_lock_refuses_rescale_or_crop_of_oversized_logo(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")

    with pytest.raises(LogoAssetLockError, match="too large for exact no-rescale"):
        LogoAssetLockCompositor(engine=_Engine()).apply(
            video_path=source,
            output_path=tmp_path / "locked.mp4",
            logo=_logo(width=1900, height=1000),
            frame_width=1920,
            frame_height=1080,
        )


def test_logo_asset_lock_fails_closed_on_conflicting_placement_cues() -> None:
    with pytest.raises(LogoAssetLockError, match="ambiguous"):
        resolve_logo_placement("top left but also bottom right")


def test_logo_asset_lock_rejects_digest_mismatch() -> None:
    with pytest.raises(LogoAssetLockError, match="digest"):
        LogoAssetLockInput(
            content=b"logo",
            mime_type="image/png",
            sha256_hex="0" * 64,
            width=200,
            height=100,
        )
