import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.video_automation.ffmpeg_media_engine import (
    FfmpegMediaEngine,
    MediaCommandResult,
)
from src.video_automation.video_editing import VideoEditExecutor
from src.video_automation.video_skills import EditKind, EditOperation, VideoSkillError


class _Resolver:
    def __init__(self, assets: dict[str, Path]) -> None:
        self.assets = assets

    def require_registered_path(self, asset_id: str) -> Path:
        return self.assets[asset_id]


class _Engine:
    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        def execute(**kwargs: object) -> MediaCommandResult:
            output = Path(str(kwargs["output_path"]))
            output.write_bytes(f"edited:{name}".encode())
            return MediaCommandResult(("ffmpeg", name), 0, "", "")

        return execute


def _input(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"input")
    return path


def test_executes_supported_edit_through_registered_assets(tmp_path: Path) -> None:
    cases: tuple[
        tuple[
            EditKind,
            tuple[str, ...],
            dict[str, str | int | float | bool],
            str,
        ],
        ...,
    ] = (
        (
            EditKind.TRIM,
            ("a",),
            {"start_seconds": 0.0, "duration_seconds": 1.0},
            "trim",
        ),
        (EditKind.CONCATENATE, ("a", "b"), {}, "concatenate"),
        (EditKind.OVERLAY, ("a", "b"), {"x": 5, "y": -2}, "overlay"),
        (
            EditKind.SCALE,
            ("a",),
            {
                "width": 720,
                "height": 1280,
                "fps": 30,
                "video_codec": "libx264",
                "audio_codec": "aac",
            },
            "normalize_video",
        ),
        (
            EditKind.CROP,
            ("a",),
            {"width": 100, "height": 200, "x": 4, "y": 8},
            "crop",
        ),
        (EditKind.AUDIO_MIX, ("a", "b"), {}, "mix_audio"),
    )
    for index, (kind, input_ids, parameters, engine_method) in enumerate(cases):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        assets = {
            asset_id: _input(case_root, f"{asset_id}.mp4") for asset_id in input_ids
        }
        operation = EditOperation(
            f"edit-{index}", kind, input_ids, f"output-{index}", parameters
        )
        result = VideoEditExecutor(
            _Resolver(assets), case_root / "outputs", engine=_Engine()
        ).execute(operation)
        assert result.command == ("ffmpeg", engine_method)
        assert result.byte_length > 0
        assert len(result.sha256_hex) == 64


def test_rejects_unknown_parameters_before_engine_execution(tmp_path: Path) -> None:
    source = _input(tmp_path, "a.mp4")
    operation = EditOperation(
        "edit-1",
        EditKind.TRIM,
        ("a",),
        "output",
        {"start_seconds": 0, "duration_seconds": 1, "shell": True},
    )
    with pytest.raises(VideoSkillError, match="unsupported"):
        VideoEditExecutor(
            _Resolver({"a": source}), tmp_path / "outputs", engine=_Engine()
        ).execute(operation)


def test_rejects_unsafe_output_identity_and_existing_output(tmp_path: Path) -> None:
    source = _input(tmp_path, "a.mp4")
    executor = VideoEditExecutor(
        _Resolver({"a": source}), tmp_path / "outputs", engine=_Engine()
    )
    unsafe = EditOperation(
        "edit-1",
        EditKind.TRIM,
        ("a",),
        "../escape",
        {"start_seconds": 0, "duration_seconds": 1},
    )
    with pytest.raises(VideoSkillError, match="unsafe"):
        executor.execute(unsafe)
    safe = EditOperation(
        "edit-2",
        EditKind.TRIM,
        ("a",),
        "output",
        {"start_seconds": 0, "duration_seconds": 1},
    )
    executor.execute(safe)
    with pytest.raises(VideoSkillError, match="already exists"):
        executor.execute(safe)


def test_rejects_broken_output_symlink(tmp_path: Path) -> None:
    source = _input(tmp_path, "a.mp4")
    output_root = tmp_path / "outputs"
    operation = EditOperation(
        "edit-1",
        EditKind.TRIM,
        ("a",),
        "output",
        {"start_seconds": 0, "duration_seconds": 1},
    )
    with (
        patch.object(Path, "is_symlink", return_value=True),
        pytest.raises(VideoSkillError, match="symbolic links"),
    ):
        VideoEditExecutor(
            _Resolver({"a": source}), output_root, engine=_Engine()
        ).execute(operation)


def test_real_ffmpeg_trim_execution_is_content_addressed(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    subprocess.run(
        (
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x284:d=2:r=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ),
        check=True,
        capture_output=True,
        timeout=30,
    )
    operation = EditOperation(
        "edit-real-1",
        EditKind.TRIM,
        ("source",),
        "trimmed",
        {"start_seconds": 0.25, "duration_seconds": 1.0},
    )
    result = VideoEditExecutor(
        _Resolver({"source": source}), tmp_path / "outputs"
    ).execute(operation)
    probe = FfmpegMediaEngine().probe(result.output_path)
    assert result.byte_length == Path(result.output_path).stat().st_size
    assert 0.8 <= probe.duration_seconds <= 1.2
