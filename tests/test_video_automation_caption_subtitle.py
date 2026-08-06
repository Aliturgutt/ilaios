"""Tests for canonical M16 Caption & Subtitle Engine."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.caption_subtitle import (
    BurnedInCaptionInstructions,
    CaptionCue,
    CaptionExportManifest,
    CaptionSubtitleEngine,
    CaptionSubtitleError,
)


def _cues() -> tuple[CaptionCue, ...]:
    return (
        CaptionCue(
            cue_id="cue-1",
            text="The signal begins.",
            start_seconds=0.0,
            end_seconds=1.25,
        ),
        CaptionCue(
            cue_id="cue-2",
            text="The origin awakens.",
            start_seconds=1.25,
            end_seconds=3.5,
        ),
    )


def test_exports_structured_json_srt_vtt_and_burn_in_instructions() -> None:
    with TemporaryDirectory() as directory_name:
        output_root = Path(directory_name)

        manifest = CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="script",
            output_directory=output_root,
        )

        assert isinstance(
            manifest,
            CaptionExportManifest,
        )

        assert manifest.job_id == "job-1"
        assert manifest.timing_source == "script"
        assert manifest.cues == _cues()

        json_path = Path(manifest.structured_json_path)
        srt_path = Path(manifest.srt_path)
        vtt_path = Path(manifest.vtt_path)

        assert json_path.is_file()
        assert srt_path.is_file()
        assert vtt_path.is_file()

        assert isinstance(
            manifest.burned_in,
            BurnedInCaptionInstructions,
        )

        assert (
            manifest.burned_in.subtitle_path
            == str(srt_path.resolve())
        )
        assert manifest.burned_in.subtitle_format == "srt"


def test_structured_json_contains_canonical_caption_data() -> None:
    with TemporaryDirectory() as directory_name:
        manifest = CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="voice_alignment",
            output_directory=directory_name,
        )

        payload = json.loads(
            Path(
                manifest.structured_json_path
            ).read_text(encoding="utf-8")
        )

        assert payload["job_id"] == "job-1"
        assert payload["timing_source"] == "voice_alignment"

        assert payload["cues"] == [
            {
                "cue_id": "cue-1",
                "index": 1,
                "start_seconds": 0.0,
                "end_seconds": 1.25,
                "text": "The signal begins.",
            },
            {
                "cue_id": "cue-2",
                "index": 2,
                "start_seconds": 1.25,
                "end_seconds": 3.5,
                "text": "The origin awakens.",
            },
        ]


def test_srt_uses_canonical_millisecond_timestamp_format() -> None:
    with TemporaryDirectory() as directory_name:
        manifest = CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="script",
            output_directory=directory_name,
        )

        srt = Path(manifest.srt_path).read_text(
            encoding="utf-8"
        )

        assert "00:00:00,000 --> 00:00:01,250" in srt
        assert "00:00:01,250 --> 00:00:03,500" in srt
        assert "The signal begins." in srt
        assert "The origin awakens." in srt


def test_vtt_uses_webvtt_header_and_period_timestamps() -> None:
    with TemporaryDirectory() as directory_name:
        manifest = CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="transcription",
            output_directory=directory_name,
        )

        vtt = Path(manifest.vtt_path).read_text(
            encoding="utf-8"
        )

        assert vtt.startswith("WEBVTT\n")
        assert "cue-1" in vtt
        assert "00:00:00.000 --> 00:00:01.250" in vtt
        assert "00:00:01.250 --> 00:00:03.500" in vtt


def test_checksums_match_written_files() -> None:
    with TemporaryDirectory() as directory_name:
        manifest = CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="script",
            output_directory=directory_name,
        )

        assert (
            sha256(
                Path(
                    manifest.structured_json_path
                ).read_bytes()
            ).hexdigest()
            == manifest.structured_json_sha256
        )

        assert (
            sha256(
                Path(manifest.srt_path).read_bytes()
            ).hexdigest()
            == manifest.srt_sha256
        )

        assert (
            sha256(
                Path(manifest.vtt_path).read_bytes()
            ).hexdigest()
            == manifest.vtt_sha256
        )


def test_export_is_deterministic() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        engine = CaptionSubtitleEngine()

        first = engine.export(
            job_id="job-1",
            cues=_cues(),
            timing_source="script",
            output_directory=root / "first",
        )

        second = engine.export(
            job_id="job-1",
            cues=_cues(),
            timing_source="script",
            output_directory=root / "second",
        )

        assert (
            Path(first.structured_json_path).name
            == Path(second.structured_json_path).name
        )

        assert (
            Path(first.srt_path).name
            == Path(second.srt_path).name
        )

        assert (
            Path(first.vtt_path).name
            == Path(second.vtt_path).name
        )

        assert (
            Path(first.structured_json_path).read_bytes()
            == Path(second.structured_json_path).read_bytes()
        )

        assert (
            Path(first.srt_path).read_bytes()
            == Path(second.srt_path).read_bytes()
        )

        assert (
            Path(first.vtt_path).read_bytes()
            == Path(second.vtt_path).read_bytes()
        )


def test_all_canonical_timing_sources_are_supported() -> None:
    for timing_source in (
        "script",
        "voice_alignment",
        "transcription",
    ):
        with TemporaryDirectory() as directory_name:
            manifest = CaptionSubtitleEngine().export(
                job_id="job-1",
                cues=_cues(),
                timing_source=timing_source,
                output_directory=directory_name,
            )

            assert manifest.timing_source == timing_source


def test_unknown_timing_source_fails_closed() -> None:
    with TemporaryDirectory() as directory_name, pytest.raises(
        CaptionSubtitleError,
        match="timing_source",
    ):
        CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=_cues(),
            timing_source="guessed",
            output_directory=directory_name,
        )


def test_duplicate_cue_ids_fail_closed() -> None:
    cues = (
        CaptionCue(
            cue_id="cue-1",
            text="First.",
            start_seconds=0.0,
            end_seconds=1.0,
        ),
        CaptionCue(
            cue_id="cue-1",
            text="Second.",
            start_seconds=1.0,
            end_seconds=2.0,
        ),
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        CaptionSubtitleError,
        match="identifiers must be unique",
    ):
        CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=cues,
            timing_source="script",
            output_directory=directory_name,
        )


def test_overlapping_cues_fail_closed() -> None:
    cues = (
        CaptionCue(
            cue_id="cue-1",
            text="First.",
            start_seconds=0.0,
            end_seconds=2.0,
        ),
        CaptionCue(
            cue_id="cue-2",
            text="Second.",
            start_seconds=1.5,
            end_seconds=3.0,
        ),
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        CaptionSubtitleError,
        match="must not overlap",
    ):
        CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=cues,
            timing_source="script",
            output_directory=directory_name,
        )


def test_invalid_cue_duration_fails_closed() -> None:
    with pytest.raises(
        CaptionSubtitleError,
        match="greater than start_seconds",
    ):
        CaptionCue(
            cue_id="cue-1",
            text="Invalid.",
            start_seconds=1.0,
            end_seconds=1.0,
        )


def test_negative_cue_start_fails_closed() -> None:
    with pytest.raises(
        CaptionSubtitleError,
        match="greater than or equal to zero",
    ):
        CaptionCue(
            cue_id="cue-1",
            text="Invalid.",
            start_seconds=-0.1,
            end_seconds=1.0,
        )


def test_empty_caption_collection_fails_closed() -> None:
    with TemporaryDirectory() as directory_name, pytest.raises(
        CaptionSubtitleError,
        match="at least one caption",
    ):
        CaptionSubtitleEngine().export(
            job_id="job-1",
            cues=(),
            timing_source="script",
            output_directory=directory_name,
        )


def test_burn_in_instruction_rejects_unknown_format() -> None:
    with pytest.raises(
        CaptionSubtitleError,
        match="either srt or vtt",
    ):
        BurnedInCaptionInstructions(
            subtitle_path="captions.txt",
            subtitle_format="txt",
        )
