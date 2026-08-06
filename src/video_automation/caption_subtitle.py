"""Canonical M16 Caption & Subtitle Engine.

M16 converts already-timed caption text into deterministic structured caption
JSON, SRT, VTT, and burned-in caption instructions.

Timing may originate upstream from script timing, voice alignment, or a
TranscriptionProvider. This module does not perform transcription, timeline
composition, rendering, or actual subtitle burn-in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

_ALLOWED_TIMING_SOURCES = frozenset(
    {
        "script",
        "voice_alignment",
        "transcription",
    }
)


class CaptionSubtitleError(ValueError):
    """Raised when canonical M16 caption generation cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class CaptionCue:
    """One canonical timed caption unit."""

    cue_id: str
    text: str
    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        _require_non_blank("cue_id", self.cue_id)
        _require_non_blank("text", self.text)

        if self.start_seconds < 0:
            raise CaptionSubtitleError(
                "start_seconds must be greater than or equal to zero"
            )

        if self.end_seconds <= self.start_seconds:
            raise CaptionSubtitleError(
                "end_seconds must be greater than start_seconds"
            )


@dataclass(frozen=True, slots=True)
class BurnedInCaptionInstructions:
    """Instructions consumed later by a composition or media engine."""

    subtitle_path: str
    subtitle_format: str

    def __post_init__(self) -> None:
        _require_non_blank("subtitle_path", self.subtitle_path)
        _require_non_blank("subtitle_format", self.subtitle_format)

        if self.subtitle_format not in {"srt", "vtt"}:
            raise CaptionSubtitleError(
                "subtitle_format must be either srt or vtt"
            )


@dataclass(frozen=True, slots=True)
class CaptionExportManifest:
    """Deterministic output manifest for one caption package."""

    job_id: str
    timing_source: str
    cues: tuple[CaptionCue, ...]
    structured_json_path: str
    structured_json_sha256: str
    srt_path: str
    srt_sha256: str
    vtt_path: str
    vtt_sha256: str
    burned_in: BurnedInCaptionInstructions

    def __post_init__(self) -> None:
        _require_non_blank("job_id", self.job_id)
        _validate_timing_source(self.timing_source)

        if not self.cues:
            raise CaptionSubtitleError(
                "caption manifest must contain at least one cue"
            )

        for name in (
            "structured_json_path",
            "srt_path",
            "vtt_path",
        ):
            _require_non_blank(name, getattr(self, name))

        for digest in (
            self.structured_json_sha256,
            self.srt_sha256,
            self.vtt_sha256,
        ):
            _validate_sha256(digest)


class CaptionSubtitleEngine:
    """Export canonical timed caption cues into M16 output formats."""

    def export(
        self,
        *,
        job_id: str,
        cues: tuple[CaptionCue, ...],
        timing_source: str,
        output_directory: str | Path,
    ) -> CaptionExportManifest:
        """Validate cues and produce deterministic JSON, SRT, and VTT."""

        _require_non_blank("job_id", job_id)
        _validate_timing_source(timing_source)
        _validate_cues(cues)

        output_root = Path(output_directory)
        output_root.mkdir(parents=True, exist_ok=True)

        identity_material = json.dumps(
            {
                "job_id": job_id,
                "timing_source": timing_source,
                "cues": [
                    {
                        "cue_id": cue.cue_id,
                        "text": cue.text,
                        "start_seconds": cue.start_seconds,
                        "end_seconds": cue.end_seconds,
                    }
                    for cue in cues
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        package_id = sha256(
            identity_material.encode("utf-8")
        ).hexdigest()[:24]

        base_name = f"captions-{package_id}"

        json_path = output_root / f"{base_name}.json"
        srt_path = output_root / f"{base_name}.srt"
        vtt_path = output_root / f"{base_name}.vtt"

        structured_json = _structured_json(
            job_id=job_id,
            timing_source=timing_source,
            cues=cues,
        )
        srt = _render_srt(cues)
        vtt = _render_vtt(cues)

        _write_text(json_path, structured_json)
        _write_text(srt_path, srt)
        _write_text(vtt_path, vtt)

        json_digest = _checksum(json_path)
        srt_digest = _checksum(srt_path)
        vtt_digest = _checksum(vtt_path)

        return CaptionExportManifest(
            job_id=job_id,
            timing_source=timing_source,
            cues=cues,
            structured_json_path=str(json_path.resolve()),
            structured_json_sha256=json_digest,
            srt_path=str(srt_path.resolve()),
            srt_sha256=srt_digest,
            vtt_path=str(vtt_path.resolve()),
            vtt_sha256=vtt_digest,
            burned_in=BurnedInCaptionInstructions(
                subtitle_path=str(srt_path.resolve()),
                subtitle_format="srt",
            ),
        )


def _validate_cues(cues: tuple[CaptionCue, ...]) -> None:
    if not cues:
        raise CaptionSubtitleError(
            "cues must contain at least one caption"
        )

    cue_ids = tuple(cue.cue_id for cue in cues)

    if len(cue_ids) != len(set(cue_ids)):
        raise CaptionSubtitleError(
            "caption cue identifiers must be unique"
        )

    previous_end = 0.0

    for index, cue in enumerate(cues):
        if index > 0 and cue.start_seconds < previous_end:
            raise CaptionSubtitleError(
                "caption cues must not overlap"
            )

        previous_end = cue.end_seconds


def _structured_json(
    *,
    job_id: str,
    timing_source: str,
    cues: tuple[CaptionCue, ...],
) -> str:
    payload = {
        "job_id": job_id,
        "timing_source": timing_source,
        "cues": [
            {
                "cue_id": cue.cue_id,
                "index": index,
                "start_seconds": cue.start_seconds,
                "end_seconds": cue.end_seconds,
                "text": cue.text,
            }
            for index, cue in enumerate(
                cues,
                start=1,
            )
        ],
    }

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _render_srt(cues: tuple[CaptionCue, ...]) -> str:
    blocks: list[str] = []

    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "\n".join(
                (
                    str(index),
                    (
                        f"{_format_timestamp(cue.start_seconds, separator=',')} "
                        f"--> "
                        f"{_format_timestamp(cue.end_seconds, separator=',')}"
                    ),
                    cue.text,
                )
            )
        )

    return "\n\n".join(blocks) + "\n"


def _render_vtt(cues: tuple[CaptionCue, ...]) -> str:
    blocks = ["WEBVTT"]

    for cue in cues:
        blocks.append(
            "\n".join(
                (
                    cue.cue_id,
                    (
                        f"{_format_timestamp(cue.start_seconds, separator='.')} "
                        f"--> "
                        f"{_format_timestamp(cue.end_seconds, separator='.')}"
                    ),
                    cue.text,
                )
            )
        )

    return "\n\n".join(blocks) + "\n"


def _format_timestamp(
    seconds: float,
    *,
    separator: str,
) -> str:
    if seconds < 0:
        raise CaptionSubtitleError(
            "timestamp seconds must not be negative"
        )

    if separator not in {",", "."}:
        raise CaptionSubtitleError(
            "timestamp separator must be comma or period"
        )

    total_milliseconds = round(seconds * 1000.0)

    hours, remainder = divmod(
        total_milliseconds,
        3_600_000,
    )

    minutes, remainder = divmod(
        remainder,
        60_000,
    )

    whole_seconds, milliseconds = divmod(
        remainder,
        1_000,
    )

    return (
        f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"
        f"{separator}{milliseconds:03d}"
    )


def _write_text(path: Path, content: str) -> None:
    try:
        path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
    except OSError as exc:
        raise CaptionSubtitleError(
            f"failed to write caption output: {path}"
        ) from exc


def _checksum(path: Path) -> str:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise CaptionSubtitleError(
            f"caption output is unreadable: {path}"
        ) from exc

    if not body:
        raise CaptionSubtitleError(
            f"caption output must not be empty: {path}"
        )

    return sha256(body).hexdigest()


def _validate_timing_source(value: str) -> None:
    _require_non_blank("timing_source", value)

    if value not in _ALLOWED_TIMING_SOURCES:
        raise CaptionSubtitleError(
            "timing_source must be script, voice_alignment, or transcription"
        )


def _validate_sha256(value: str) -> None:
    if len(value) != 64:
        raise CaptionSubtitleError(
            "caption checksum must contain 64 hexadecimal characters"
        )

    try:
        int(value, 16)
    except ValueError as exc:
        raise CaptionSubtitleError(
            "caption checksum must contain 64 hexadecimal characters"
        ) from exc


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise CaptionSubtitleError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise CaptionSubtitleError(
            f"{name} must not contain surrounding whitespace"
        )
