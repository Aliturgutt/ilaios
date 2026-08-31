"""Real pixel-level Remotion executor for canonical M20 rendering.

The renderer remains behind the existing RenderExecutor contract. Remotion owns
visual frame generation; canonical FFmpeg is used only to attach a deterministic
silent audio stream required by the existing M20 RenderArtifact contract.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .ffmpeg_media_engine import CommandRunner, SubprocessCommandRunner
from .render_engine import (
    RenderEngineError,
    RenderExecutionRequest,
    RenderExecutionResult,
)

_REMOTION_RENDERER_ID = "remotion-renderer-4.0.518-v1"


class RemotionCliRenderExecutor:
    """Execute the repo-managed Remotion runtime without shell interpolation."""

    def __init__(
        self,
        *,
        node_executable: str = "node",
        ffmpeg_executable: str = "ffmpeg",
        runtime_script: str | Path | None = None,
        runner: CommandRunner | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        _require_non_blank("node_executable", node_executable)
        _require_non_blank("ffmpeg_executable", ffmpeg_executable)
        if timeout_seconds <= 0:
            raise RenderEngineError("timeout_seconds must be greater than zero")

        default_runtime = (
            Path(__file__).resolve().parents[2]
            / "tools"
            / "video_remotion_runtime"
            / "render.mjs"
        )
        self._node = node_executable
        self._ffmpeg = ffmpeg_executable
        self._runtime_script = Path(runtime_script or default_runtime).resolve()
        self._runner = runner or SubprocessCommandRunner()
        self._timeout_seconds = timeout_seconds

    def execute(self, request: RenderExecutionRequest) -> RenderExecutionResult:
        runtime_script = self._runtime_script
        if not runtime_script.exists() or not runtime_script.is_file():
            raise RenderEngineError("repo-managed Remotion runtime is unavailable")

        manifest_path = Path(request.composition.manifest_path).resolve()
        payload = _read_manifest(manifest_path)
        composition = _require_mapping(payload, "composition")

        _require_manifest_match(
            composition=composition,
            duration_seconds=request.composition.duration_seconds,
            fps=request.composition.fps,
            width=request.composition.width,
            height=request.composition.height,
        )

        output_path = Path(request.output_path).resolve()
        if output_path.exists() and output_path.is_dir():
            raise RenderEngineError("output_path must reference a file")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        visual_path = output_path.with_suffix(output_path.suffix + ".remotion-video.mp4")
        for stale in (visual_path, output_path):
            if stale.exists():
                if not stale.is_file():
                    raise RenderEngineError("render output path must reference a file")
                stale.unlink()

        try:
            self._runner.run(
                (
                    self._node,
                    str(runtime_script),
                    str(manifest_path),
                    str(visual_path),
                ),
                timeout_seconds=self._timeout_seconds,
            )
            _require_non_empty_file(visual_path, "Remotion visual render")

            self._runner.run(
                (
                    self._ffmpeg,
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(visual_path),
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-t",
                    _format_number(request.composition.duration_seconds),
                    "-shortest",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ),
                timeout_seconds=self._timeout_seconds,
            )
            _require_non_empty_file(output_path, "final Remotion render")
        finally:
            if visual_path.exists() and visual_path.is_file():
                visual_path.unlink()

        return RenderExecutionResult(
            output_path=str(output_path),
            renderer_id=_REMOTION_RENDERER_ID,
        )


def _read_manifest(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderEngineError("Remotion composition manifest is unreadable or invalid") from exc
    if not isinstance(payload, dict):
        raise RenderEngineError("Remotion composition manifest root must be an object")
    if payload.get("schema_version") != 1 or payload.get("engine") != "remotion":
        raise RenderEngineError("unsupported Remotion composition manifest")
    if not isinstance(payload.get("elements"), list) or not isinstance(payload.get("timeline"), list):
        raise RenderEngineError("Remotion composition manifest requires timeline and elements")
    return payload


def _require_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RenderEngineError(f"Remotion composition manifest requires {key} object")
    return value


def _require_manifest_match(
    *,
    composition: Mapping[str, object],
    duration_seconds: float,
    fps: int,
    width: int,
    height: int,
) -> None:
    expected = {
        "fps": fps,
        "width": width,
        "height": height,
        "duration_frames": round(duration_seconds * fps),
    }
    for key, expected_value in expected.items():
        value = composition.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value != expected_value:
            raise RenderEngineError(f"manifest {key} does not match composition artifact")

    raw_duration = composition.get("duration_seconds")
    if isinstance(raw_duration, bool) or not isinstance(raw_duration, (int, float)):
        raise RenderEngineError("manifest duration_seconds must be numeric")
    if abs(float(raw_duration) - duration_seconds) > 1e-9:
        raise RenderEngineError("manifest duration does not match composition artifact")


def _require_non_empty_file(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise RenderEngineError(f"{label} did not create a non-empty file")


def _format_number(value: float) -> str:
    return format(value, ".9g")


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise RenderEngineError(f"{name} must be a non-blank trimmed string")
