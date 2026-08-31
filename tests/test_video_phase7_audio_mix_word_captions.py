from __future__ import annotations

import wave
from array import array
from hashlib import sha256
from pathlib import Path

import pytest

from video_automation.audio_mix import AudioMixError, mix_processed_audio
from video_automation.audio_processing import AudioProcessingManifest
from video_automation.models import MediaAsset, MediaType
from video_automation.word_synced_captions import (
    WordSyncedCaptionError,
    WordTiming,
    export_word_synced_captions,
)


def _write_wav(path: Path, samples: tuple[int, ...], *, sample_rate: int = 8_000) -> None:
    values = array("h", samples)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(values.tobytes())


def _asset(
    *,
    path: Path,
    asset_id: str,
    media_type: MediaType,
    job_id: str = "job-video-phase7",
) -> MediaAsset:
    return MediaAsset(
        asset_id=asset_id,
        job_id=job_id,
        media_type=media_type,
        file_path=str(path),
        checksum_sha256=sha256(path.read_bytes()).hexdigest(),
        provider_name="local-test",
        source_reference=f"test://{asset_id}",
        validated=True,
    )


def _read_samples(path: Path) -> tuple[int, ...]:
    with wave.open(str(path), "rb") as wav_file:
        values = array("h")
        values.frombytes(wav_file.readframes(wav_file.getnframes()))
    return tuple(int(value) for value in values)


def test_final_mix_ducks_music_only_while_narration_is_active(tmp_path: Path) -> None:
    narration_path = tmp_path / "narration.wav"
    music_path = tmp_path / "music.wav"
    sfx_path = tmp_path / "sfx.wav"
    _write_wav(narration_path, (1_000, 1_000, 0, 0))
    _write_wav(music_path, (1_000, 1_000, 1_000, 1_000))
    _write_wav(sfx_path, (100, 100, 100, 100))

    manifest = AudioProcessingManifest(
        job_id="job-video-phase7",
        narration_asset=_asset(
            path=narration_path,
            asset_id="voice",
            media_type=MediaType.VOICE,
        ),
        music_assets=(
            _asset(path=music_path, asset_id="music", media_type=MediaType.MUSIC),
        ),
        sound_effect_assets=(
            _asset(
                path=sfx_path,
                asset_id="sfx",
                media_type=MediaType.SOUND_EFFECT,
            ),
        ),
        target_duration_seconds=0.0005,
        sample_rate=8_000,
    )

    result = mix_processed_audio(manifest=manifest, output_directory=tmp_path / "mix")

    assert result.narration_active_frames == 2
    assert result.ducked_music_frames == 2
    assert result.music_track_count == 1
    assert result.sound_effect_track_count == 1
    assert result.frame_count == 4
    assert _read_samples(Path(result.output_path)) == (1_205, 1_205, 405, 405)
    assert sha256(Path(result.output_path).read_bytes()).hexdigest() == result.checksum_sha256


def test_final_mix_fails_closed_on_changed_audio_bytes(tmp_path: Path) -> None:
    narration_path = tmp_path / "narration.wav"
    _write_wav(narration_path, (1_000, 1_000))
    narration = _asset(
        path=narration_path,
        asset_id="voice",
        media_type=MediaType.VOICE,
    )
    narration_path.write_bytes(narration_path.read_bytes() + b"tamper")
    manifest = AudioProcessingManifest(
        job_id="job-video-phase7",
        narration_asset=narration,
        music_assets=(),
        sound_effect_assets=(),
        target_duration_seconds=0.00025,
        sample_rate=8_000,
    )

    with pytest.raises(AudioMixError, match="checksum mismatch"):
        mix_processed_audio(manifest=manifest, output_directory=tmp_path / "mix")


def test_word_synced_captions_preserve_proven_word_boundaries(tmp_path: Path) -> None:
    words = (
        WordTiming("One", 0.10, 0.30),
        WordTiming("prompt", 0.32, 0.60),
        WordTiming("finished", 0.90, 1.20),
        WordTiming("video", 1.22, 1.50),
    )

    result = export_word_synced_captions(
        job_id="job-video-phase7",
        words=words,
        timing_source="voice_alignment",
        output_directory=tmp_path / "captions",
        max_words_per_cue=2,
    )

    assert result.words == words
    assert tuple(cue.text for cue in result.export.cues) == (
        "One prompt",
        "finished video",
    )
    assert result.export.cues[0].start_seconds == 0.10
    assert result.export.cues[0].end_seconds == 0.60
    assert result.export.cues[1].start_seconds == 0.90
    assert result.export.cues[1].end_seconds == 1.50
    assert Path(result.export.srt_path).is_file()
    assert Path(result.export.vtt_path).is_file()


def test_word_synced_captions_reject_overlapping_word_timing(tmp_path: Path) -> None:
    words = (
        WordTiming("bad", 0.10, 0.40),
        WordTiming("overlap", 0.30, 0.60),
    )

    with pytest.raises(WordSyncedCaptionError, match="must not overlap"):
        export_word_synced_captions(
            job_id="job-video-phase7",
            words=words,
            timing_source="transcription",
            output_directory=tmp_path,
        )
