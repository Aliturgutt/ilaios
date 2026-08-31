"""Word-timed caption alignment for the canonical M16 caption engine.

This module converts validated word-level timing evidence into non-overlapping
M16 caption cues and delegates JSON/SRT/VTT export to ``CaptionSubtitleEngine``.
It does not transcribe audio or invent timing data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .caption_subtitle import CaptionExportManifest, CaptionCue, CaptionSubtitleEngine


class WordSyncedCaptionError(ValueError):
    """Raised when word-level caption timing cannot be accepted safely."""


@dataclass(frozen=True, slots=True)
class WordTiming:
    """One upstream-proven word timing interval."""

    word: str
    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        if not self.word or self.word != self.word.strip():
            raise WordSyncedCaptionError("word must be non-blank and trimmed")
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise WordSyncedCaptionError("word timing interval is invalid")


@dataclass(frozen=True, slots=True)
class WordSyncedCaptionManifest:
    """Word-level evidence plus the canonical M16 export derived from it."""

    job_id: str
    words: tuple[WordTiming, ...]
    export: CaptionExportManifest

    def __post_init__(self) -> None:
        if not self.job_id or self.job_id != self.job_id.strip():
            raise WordSyncedCaptionError("job_id must be non-blank and trimmed")
        if not self.words:
            raise WordSyncedCaptionError("word timing evidence must not be empty")
        if self.export.job_id != self.job_id:
            raise WordSyncedCaptionError("caption export job_id mismatch")
        if self.export.timing_source not in {"voice_alignment", "transcription"}:
            raise WordSyncedCaptionError("word-synced captions require aligned timing evidence")


def export_word_synced_captions(
    *,
    job_id: str,
    words: tuple[WordTiming, ...],
    timing_source: str,
    output_directory: str | Path,
    max_words_per_cue: int = 4,
    max_gap_seconds: float = 0.45,
) -> WordSyncedCaptionManifest:
    """Validate word timing, group it deterministically, and export through M16."""

    if not job_id or job_id != job_id.strip():
        raise WordSyncedCaptionError("job_id must be non-blank and trimmed")
    if not words:
        raise WordSyncedCaptionError("words must contain word-level timing evidence")
    if timing_source not in {"voice_alignment", "transcription"}:
        raise WordSyncedCaptionError(
            "timing_source must be voice_alignment or transcription for word sync"
        )
    if max_words_per_cue <= 0:
        raise WordSyncedCaptionError("max_words_per_cue must be positive")
    if max_gap_seconds < 0:
        raise WordSyncedCaptionError("max_gap_seconds must not be negative")

    previous_end = 0.0
    for index, word in enumerate(words):
        if index > 0 and word.start_seconds < previous_end:
            raise WordSyncedCaptionError("word timing intervals must not overlap")
        previous_end = word.end_seconds

    cue_groups: list[list[WordTiming]] = []
    current: list[WordTiming] = []

    for word in words:
        if current:
            gap = word.start_seconds - current[-1].end_seconds
            if len(current) >= max_words_per_cue or gap > max_gap_seconds:
                cue_groups.append(current)
                current = []
        current.append(word)
    if current:
        cue_groups.append(current)

    cues = tuple(
        CaptionCue(
            cue_id=f"word-sync-{index:04d}",
            text=" ".join(word.word for word in group),
            start_seconds=group[0].start_seconds,
            end_seconds=group[-1].end_seconds,
        )
        for index, group in enumerate(cue_groups, start=1)
    )

    export = CaptionSubtitleEngine().export(
        job_id=job_id,
        cues=cues,
        timing_source=timing_source,
        output_directory=output_directory,
    )
    return WordSyncedCaptionManifest(job_id=job_id, words=words, export=export)
