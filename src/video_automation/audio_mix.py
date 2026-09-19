"""Deterministic final PCM audio mix for canonical Video Factory tracks.

Consumes the M15 ``AudioProcessingManifest`` and produces one mono 16-bit PCM
WAV mix. Narration remains authoritative; music is ducked while narration is
active and sound effects are mixed at a bounded gain. This module performs no
provider calls, codec muxing, policy decisions, or evidence-authority work.
"""

from __future__ import annotations

import sys
import wave
from array import array
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .audio_processing import AudioProcessingManifest

_SAMPLE_WIDTH_BYTES = 2
_CHANNELS = 1
_NARRATION_ACTIVE_THRESHOLD = 384
_MUSIC_GAIN = 0.35
_MUSIC_DUCKED_GAIN = 0.15
_SFX_GAIN = 0.55


class AudioMixError(ValueError):
    """Raised when a canonical final audio mix cannot be produced safely."""


@dataclass(frozen=True, slots=True)
class AudioMixManifest:
    """Evidence-bearing result of one deterministic PCM mix."""

    job_id: str
    output_path: str
    checksum_sha256: str
    sample_rate: int
    frame_count: int
    narration_active_frames: int
    ducked_music_frames: int
    music_track_count: int
    sound_effect_track_count: int

    def __post_init__(self) -> None:
        if not self.job_id or self.job_id != self.job_id.strip():
            raise AudioMixError("job_id must be non-blank and trimmed")
        if self.sample_rate <= 0 or self.frame_count <= 0:
            raise AudioMixError("sample_rate and frame_count must be positive")
        if len(self.checksum_sha256) != 64:
            raise AudioMixError("checksum_sha256 must be a SHA-256 digest")
        try:
            int(self.checksum_sha256, 16)
        except ValueError as exc:
            raise AudioMixError("checksum_sha256 must be hexadecimal") from exc
        if not 0 <= self.narration_active_frames <= self.frame_count:
            raise AudioMixError("invalid narration_active_frames")
        if not 0 <= self.ducked_music_frames <= self.frame_count:
            raise AudioMixError("invalid ducked_music_frames")
        if self.music_track_count < 0 or self.sound_effect_track_count < 0:
            raise AudioMixError("track counts must not be negative")


def mix_processed_audio(
    *,
    manifest: AudioProcessingManifest,
    output_directory: str | Path,
) -> AudioMixManifest:
    """Mix one processed M15 manifest with deterministic narration ducking."""

    narration = _load_verified_track(
        path=Path(manifest.narration_asset.file_path),
        expected_checksum=manifest.narration_asset.checksum_sha256,
    )
    music_tracks = tuple(
        _load_verified_track(
            path=Path(asset.file_path),
            expected_checksum=asset.checksum_sha256,
        )
        for asset in manifest.music_assets
    )
    sfx_tracks = tuple(
        _load_verified_track(
            path=Path(asset.file_path),
            expected_checksum=asset.checksum_sha256,
        )
        for asset in manifest.sound_effect_assets
    )

    expected_frames = len(narration.samples)
    for track in (*music_tracks, *sfx_tracks):
        if track.sample_rate != narration.sample_rate:
            raise AudioMixError("all final-mix tracks must share one sample rate")
        if len(track.samples) != expected_frames:
            raise AudioMixError("all final-mix tracks must share one frame count")

    mixed: list[int] = []
    narration_active_frames = 0
    ducked_music_frames = 0

    for index, narration_sample in enumerate(narration.samples):
        narration_active = abs(narration_sample) > _NARRATION_ACTIVE_THRESHOLD
        if narration_active:
            narration_active_frames += 1

        value = float(narration_sample)

        if music_tracks:
            music_gain = _MUSIC_DUCKED_GAIN if narration_active else _MUSIC_GAIN
            if narration_active:
                ducked_music_frames += 1
            value += sum(track.samples[index] * music_gain for track in music_tracks)

        value += sum(track.samples[index] * _SFX_GAIN for track in sfx_tracks)
        mixed.append(_clamp_int16(round(value)))

    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)
    identity = "\n".join(
        (
            manifest.job_id,
            manifest.narration_asset.checksum_sha256,
            *(asset.checksum_sha256 for asset in manifest.music_assets),
            *(asset.checksum_sha256 for asset in manifest.sound_effect_assets),
            f"music_gain={_MUSIC_GAIN}",
            f"music_ducked_gain={_MUSIC_DUCKED_GAIN}",
            f"sfx_gain={_SFX_GAIN}",
            f"narration_threshold={_NARRATION_ACTIVE_THRESHOLD}",
        )
    )
    mix_id = sha256(identity.encode("utf-8")).hexdigest()[:24]
    output_path = output_root / f"audio-mix-{mix_id}.wav"
    _write_track(
        output_path,
        sample_rate=narration.sample_rate,
        samples=tuple(mixed),
    )
    body = output_path.read_bytes()
    if not body:
        raise AudioMixError("final audio mix output must not be empty")

    return AudioMixManifest(
        job_id=manifest.job_id,
        output_path=str(output_path.resolve()),
        checksum_sha256=sha256(body).hexdigest(),
        sample_rate=narration.sample_rate,
        frame_count=len(mixed),
        narration_active_frames=narration_active_frames,
        ducked_music_frames=ducked_music_frames,
        music_track_count=len(music_tracks),
        sound_effect_track_count=len(sfx_tracks),
    )


@dataclass(frozen=True, slots=True)
class _Track:
    sample_rate: int
    samples: tuple[int, ...]


def _load_verified_track(*, path: Path, expected_checksum: str) -> _Track:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise AudioMixError(f"audio track is unreadable: {path}") from exc
    if not body or sha256(body).hexdigest() != expected_checksum:
        raise AudioMixError(f"audio track checksum mismatch: {path}")

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression_type = wav_file.getcomptype()
            raw_frames = wav_file.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        raise AudioMixError(f"audio track is not a readable WAV: {path}") from exc

    if channels != _CHANNELS or sample_width != _SAMPLE_WIDTH_BYTES:
        raise AudioMixError("final mix requires mono 16-bit PCM WAV tracks")
    if sample_rate <= 0 or frame_count <= 0 or compression_type != "NONE":
        raise AudioMixError("final mix requires non-empty uncompressed PCM WAV tracks")

    values = array("h")
    values.frombytes(raw_frames)
    if sys.byteorder != "little":
        values.byteswap()
    samples = tuple(int(value) for value in values)
    if len(samples) != frame_count:
        raise AudioMixError("decoded PCM frame count mismatch")
    return _Track(sample_rate=sample_rate, samples=samples)


def _write_track(path: Path, *, sample_rate: int, samples: tuple[int, ...]) -> None:
    values = array("h", (_clamp_int16(sample) for sample in samples))
    if sys.byteorder != "little":
        values.byteswap()
    try:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(_CHANNELS)
            wav_file.setsampwidth(_SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(values.tobytes())
    except (OSError, wave.Error) as exc:
        raise AudioMixError(f"failed to write final audio mix: {path}") from exc


def _clamp_int16(value: int) -> int:
    return max(-32_768, min(32_767, value))
