"""Local-only caption derivative rendering that preserves the clean master."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .caption_policy import resolve_caption_policy
from .caption_subtitle import CaptionCue, CaptionExportManifest, CaptionSubtitleEngine
from .platform_profiles import PlatformProfile
from .request_manifest import EpisodeRequestManifest


class CaptionRenderError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CaptionedVideoArtifact:
    clean_master_path: str
    clean_master_sha256: str
    captioned_video_path: str
    captioned_video_sha256: str
    captions: CaptionExportManifest
    renderer_id: str


class CaptionRenderer(Protocol):
    @property
    def renderer_id(self) -> str: ...

    def burn_in(self, *, clean: Path, subtitle: Path, output: Path) -> None: ...


class FfmpegCaptionRenderer:
    def __init__(self, executable: str = "ffmpeg", timeout_seconds: float = 600.0) -> None:
        if not executable.strip() or timeout_seconds <= 0:
            raise CaptionRenderError("invalid ffmpeg renderer configuration")
        self._executable = executable
        self._timeout = timeout_seconds

    @property
    def renderer_id(self) -> str:
        return "ffmpeg-local-caption-v1"

    def burn_in(self, *, clean: Path, subtitle: Path, output: Path) -> None:
        if clean.resolve() == output.resolve():
            raise CaptionRenderError("caption variant must not overwrite clean master")
        output.parent.mkdir(parents=True, exist_ok=True)
        escaped = str(subtitle.resolve()).replace("\\", "/")
        escaped = escaped.replace(":", r"\:").replace("'", r"\'")
        command = (
            self._executable,
            "-y",
            "-v",
            "error",
            "-i",
            str(clean),
            "-vf",
            f"subtitles='{escaped}'",
            "-c:a",
            "copy",
            str(output),
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise CaptionRenderError("local ffmpeg caption render unavailable") from exc
        if completed.returncode != 0:
            raise CaptionRenderError(
                f"local ffmpeg caption render failed: {completed.stderr.strip()}"
            )


class CaptionPostProcessor:
    def __init__(
        self,
        *,
        subtitle_engine: CaptionSubtitleEngine | None = None,
        renderer: CaptionRenderer | None = None,
    ) -> None:
        self._subtitles = subtitle_engine or CaptionSubtitleEngine()
        self._renderer = renderer or FfmpegCaptionRenderer()

    def process(
        self,
        *,
        manifest: EpisodeRequestManifest,
        platform_profile: PlatformProfile | None,
        clean_master_path: str | Path,
        cues: tuple[CaptionCue, ...],
        timing_source: str,
        output_directory: str | Path,
    ) -> CaptionedVideoArtifact | None:
        decision = resolve_caption_policy(
            manifest=manifest, platform_profile=platform_profile
        )
        if not decision.effective_enabled:
            return None
        clean = Path(clean_master_path)
        clean_body = _read(clean, "clean master")
        clean_sha = sha256(clean_body).hexdigest()
        root = Path(output_directory)
        captions = self._subtitles.export(
            job_id=manifest.episode_id,
            cues=cues,
            timing_source=timing_source,
            output_directory=root / "captions",
        )
        output = root / f"{manifest.episode_id}.captioned{clean.suffix or '.mp4'}"
        self._renderer.burn_in(
            clean=clean,
            subtitle=Path(captions.srt_path),
            output=output,
        )
        if sha256(_read(clean, "clean master")).hexdigest() != clean_sha:
            raise CaptionRenderError("caption render mutated clean master")
        captioned = _read(output, "captioned video")
        return CaptionedVideoArtifact(
            str(clean.resolve()),
            clean_sha,
            str(output.resolve()),
            sha256(captioned).hexdigest(),
            captions,
            self._renderer.renderer_id,
        )


def _read(path: Path, label: str) -> bytes:
    if not path.exists() or not path.is_file():
        raise CaptionRenderError(f"{label} does not exist")
    body = path.read_bytes()
    if not body:
        raise CaptionRenderError(f"{label} must not be empty")
    return body
