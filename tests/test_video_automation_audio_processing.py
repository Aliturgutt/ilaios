"""Tests for canonical M15 Audio Processing."""

from __future__ import annotations

import sys
import wave
from array import array
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.audio_processing import (
    AudioProcessingCoordinator,
    AudioProcessingError,
    AudioProcessingManifest,
)
from src.video_automation.models import MediaAsset, MediaType

_SAMPLE_RATE = 16_000


def _write_wav(
    path: Path,
    samples: tuple[int, ...],
    *,
    sample_rate: int = _SAMPLE_RATE,
) -> None:
    values = array("h", samples)

    if sys.byteorder != "little":
        values.byteswap()

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(values.tobytes())


def _asset(
    path: Path,
    *,
    asset_id: str,
    media_type: MediaType,
    job_id: str = "job-1",
) -> MediaAsset:
    body = path.read_bytes()

    return MediaAsset(
        asset_id=asset_id,
        job_id=job_id,
        media_type=media_type,
        file_path=str(path.resolve()),
        checksum_sha256=sha256(body).hexdigest(),
        provider_name="test-provider",
        source_reference=f"local://{path.name}",
        validated=False,
    )


def _signal() -> tuple[int, ...]:
    return (
        (0,) * 200
        + (100,) * 100
        + (1_000, -2_000, 3_000, -4_000) * 1_000
        + (100,) * 100
        + (0,) * 200
    )


def _read_samples(path: Path) -> tuple[int, ...]:
    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2

        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    values = array("h")
    values.frombytes(raw)

    if sys.byteorder != "little":
        values.byteswap()

    return tuple(int(value) for value in values)


def test_prepare_voice_produces_validated_aligned_pcm_asset() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(voice_path, _signal())

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        coordinator = AudioProcessingCoordinator()

        manifest = coordinator.prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "processed",
            target_duration_seconds=1.0,
        )

        assert isinstance(manifest, AudioProcessingManifest)
        assert manifest.job_id == "job-1"
        assert manifest.sample_rate == _SAMPLE_RATE
        assert manifest.target_duration_seconds == 1.0

        processed = manifest.narration_asset

        assert processed.media_type is MediaType.VOICE
        assert processed.job_id == "job-1"
        assert processed.validated is True
        assert processed.asset_id.startswith("audio-")

        output_path = Path(processed.file_path)

        assert output_path.exists()
        assert output_path.is_file()
        assert (
            sha256(output_path.read_bytes()).hexdigest()
            == processed.checksum_sha256
        )

        samples = _read_samples(output_path)

        assert len(samples) == _SAMPLE_RATE
        assert samples[0] != 0
        assert max(abs(sample) for sample in samples) == 26_214


def test_noise_floor_and_edge_silence_are_removed_before_alignment() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"

        samples = (
            (0,) * 50
            + (100,) * 50
            + (2_000, -2_000) * 100
            + (100,) * 50
            + (0,) * 50
        )

        _write_wav(voice_path, samples)

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        manifest = AudioProcessingCoordinator().prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "processed",
            target_duration_seconds=0.1,
        )

        processed_samples = _read_samples(
            Path(manifest.narration_asset.file_path)
        )

        assert processed_samples[0] != 0
        assert max(abs(sample) for sample in processed_samples) == 26_214


def test_short_audio_is_zero_padded_to_target_duration() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(
            voice_path,
            (2_000, -2_000) * 100,
        )

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        manifest = AudioProcessingCoordinator().prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "processed",
            target_duration_seconds=1.0,
        )

        samples = _read_samples(
            Path(manifest.narration_asset.file_path)
        )

        assert len(samples) == _SAMPLE_RATE
        assert samples[-1] == 0


def test_long_audio_is_truncated_to_target_duration() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(
            voice_path,
            (1_000, -1_000) * 20_000,
        )

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        manifest = AudioProcessingCoordinator().prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "processed",
            target_duration_seconds=0.5,
        )

        samples = _read_samples(
            Path(manifest.narration_asset.file_path)
        )

        assert len(samples) == 8_000


def test_music_and_sound_effect_assets_are_prepared_without_mixing() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        music_path = root / "music.wav"
        sfx_path = root / "sfx.wav"

        _write_wav(
            voice_path,
            (1_000, -1_000) * 2_000,
        )
        _write_wav(
            music_path,
            (800, -800) * 2_000,
        )
        _write_wav(
            sfx_path,
            (1_500, -1_500) * 1_000,
        )

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )
        music = _asset(
            music_path,
            asset_id="music-1",
            media_type=MediaType.MUSIC,
        )
        sfx = _asset(
            sfx_path,
            asset_id="sfx-1",
            media_type=MediaType.SOUND_EFFECT,
        )

        manifest = AudioProcessingCoordinator().prepare(
            job_id="job-1",
            voice_asset=voice,
            music_assets=(music,),
            sound_effect_assets=(sfx,),
            output_directory=root / "processed",
            target_duration_seconds=1.0,
        )

        assert len(manifest.music_assets) == 1
        assert len(manifest.sound_effect_assets) == 1

        prepared_music = manifest.music_assets[0]
        prepared_sfx = manifest.sound_effect_assets[0]

        assert prepared_music.media_type is MediaType.MUSIC
        assert prepared_sfx.media_type is MediaType.SOUND_EFFECT

        assert prepared_music.validated is True
        assert prepared_sfx.validated is True

        assert (
            len(_read_samples(Path(prepared_music.file_path)))
            == _SAMPLE_RATE
        )

        assert (
            len(_read_samples(Path(prepared_sfx.file_path)))
            == _SAMPLE_RATE
        )

        assert (
            manifest.narration_asset.file_path
            != prepared_music.file_path
        )
        assert prepared_music.file_path != prepared_sfx.file_path


def test_processing_does_not_modify_source_asset() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(voice_path, _signal())

        before = voice_path.read_bytes()

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        AudioProcessingCoordinator().prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "processed",
            target_duration_seconds=1.0,
        )

        assert voice_path.read_bytes() == before


def test_processing_is_deterministic() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(voice_path, _signal())

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        coordinator = AudioProcessingCoordinator()

        first = coordinator.prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "first",
            target_duration_seconds=1.0,
        )

        second = coordinator.prepare(
            job_id="job-1",
            voice_asset=voice,
            output_directory=root / "second",
            target_duration_seconds=1.0,
        )

        first_asset = first.narration_asset
        second_asset = second.narration_asset

        assert first_asset.asset_id == second_asset.asset_id
        assert first_asset.checksum_sha256 == second_asset.checksum_sha256

        assert (
            Path(first_asset.file_path).read_bytes()
            == Path(second_asset.file_path).read_bytes()
        )


def test_source_checksum_mutation_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(voice_path, _signal())

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        voice_path.write_bytes(
            voice_path.read_bytes() + b"changed"
        )

        with pytest.raises(
            AudioProcessingError,
            match="checksum changed",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=voice,
                output_directory=root / "processed",
                target_duration_seconds=1.0,
            )


def test_wrong_voice_media_type_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        path = root / "audio.wav"
        _write_wav(path, _signal())

        wrong_asset = _asset(
            path,
            asset_id="audio-1",
            media_type=MediaType.MUSIC,
        )

        with pytest.raises(
            AudioProcessingError,
            match="MediaType.VOICE",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=wrong_asset,
                output_directory=root / "processed",
                target_duration_seconds=1.0,
            )


def test_auxiliary_job_mismatch_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        music_path = root / "music.wav"

        _write_wav(voice_path, _signal())
        _write_wav(music_path, _signal())

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        music = _asset(
            music_path,
            asset_id="music-1",
            media_type=MediaType.MUSIC,
            job_id="other-job",
        )

        with pytest.raises(
            AudioProcessingError,
            match="music asset job_id",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=voice,
                music_assets=(music,),
                output_directory=root / "processed",
                target_duration_seconds=1.0,
            )


def test_sample_rate_mismatch_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        music_path = root / "music.wav"

        _write_wav(
            voice_path,
            _signal(),
            sample_rate=16_000,
        )

        _write_wav(
            music_path,
            _signal(),
            sample_rate=8_000,
        )

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        music = _asset(
            music_path,
            asset_id="music-1",
            media_type=MediaType.MUSIC,
        )

        with pytest.raises(
            AudioProcessingError,
            match="narration sample rate",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=voice,
                music_assets=(music,),
                output_directory=root / "processed",
                target_duration_seconds=1.0,
            )


def test_silence_only_track_fails_closed() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"

        _write_wav(
            voice_path,
            (0,) * 2_000,
        )

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        with pytest.raises(
            AudioProcessingError,
            match="noise floor",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=voice,
                output_directory=root / "processed",
                target_duration_seconds=1.0,
            )


def test_target_duration_must_be_positive() -> None:
    with TemporaryDirectory() as directory_name:
        root = Path(directory_name)

        voice_path = root / "voice.wav"
        _write_wav(voice_path, _signal())

        voice = _asset(
            voice_path,
            asset_id="voice-1",
            media_type=MediaType.VOICE,
        )

        with pytest.raises(
            AudioProcessingError,
            match="target_duration_seconds",
        ):
            AudioProcessingCoordinator().prepare(
                job_id="job-1",
                voice_asset=voice,
                output_directory=root / "processed",
                target_duration_seconds=0.0,
            )
