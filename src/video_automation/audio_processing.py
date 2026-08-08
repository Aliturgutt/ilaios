"""Canonical M15 audio processing for ILAIOS Video Automation.

M15 prepares deterministic, technically validated PCM audio tracks for later
timeline composition and media-engine mixing.

Responsibilities implemented here:

- audio validation
- silence/noise-floor cleanup
- deterministic peak normalization
- duration/timeline alignment
- narration preparation
- music preparation
- sound-effect preparation
- final-mix-ready track preparation

Actual cross-track mixing, muxing, codec conversion, and general-purpose
FFmpeg operations remain outside this module and belong to later media-engine
responsibilities.
"""

from __future__ import annotations

import sys
import wave
from array import array
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .models import MediaAsset, MediaType

_SAMPLE_WIDTH_BYTES = 2
_CHANNELS = 1
_TARGET_PEAK = 26_214
_NOISE_GATE_THRESHOLD = 192


class AudioProcessingError(ValueError):
    """Raised when canonical M15 audio preparation cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class AudioProcessingManifest:
    """Final-mix-ready collection of processed canonical audio assets."""

    job_id: str
    narration_asset: MediaAsset
    music_assets: tuple[MediaAsset, ...]
    sound_effect_assets: tuple[MediaAsset, ...]
    target_duration_seconds: float
    sample_rate: int

    def __post_init__(self) -> None:
        _require_non_blank("job_id", self.job_id)

        if self.target_duration_seconds <= 0:
            raise AudioProcessingError(
                "target_duration_seconds must be greater than zero"
            )

        if self.sample_rate <= 0:
            raise AudioProcessingError(
                "sample_rate must be greater than zero"
            )

        if self.narration_asset.job_id != self.job_id:
            raise AudioProcessingError(
                "narration asset job_id does not match manifest job_id"
            )

        if self.narration_asset.media_type is not MediaType.VOICE:
            raise AudioProcessingError(
                "narration asset must use MediaType.VOICE"
            )

        for asset in self.music_assets:
            if asset.job_id != self.job_id:
                raise AudioProcessingError(
                    "music asset job_id does not match manifest job_id"
                )

            if asset.media_type is not MediaType.MUSIC:
                raise AudioProcessingError(
                    "music asset must use MediaType.MUSIC"
                )

        for asset in self.sound_effect_assets:
            if asset.job_id != self.job_id:
                raise AudioProcessingError(
                    "sound-effect asset job_id does not match manifest job_id"
                )

            if asset.media_type is not MediaType.SOUND_EFFECT:
                raise AudioProcessingError(
                    "sound-effect asset must use MediaType.SOUND_EFFECT"
                )


@dataclass(frozen=True, slots=True)
class _PcmTrack:
    sample_rate: int
    samples: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise AudioProcessingError(
                "PCM sample_rate must be greater than zero"
            )

        if not self.samples:
            raise AudioProcessingError(
                "PCM track must contain at least one sample"
            )


class AudioProcessingCoordinator:
    """Prepare canonical voice/music/SFX assets for downstream composition."""

    def prepare(
        self,
        *,
        job_id: str,
        voice_asset: MediaAsset,
        output_directory: str | Path,
        target_duration_seconds: float,
        music_assets: tuple[MediaAsset, ...] = (),
        sound_effect_assets: tuple[MediaAsset, ...] = (),
    ) -> AudioProcessingManifest:
        """Validate, clean, normalize, and align all supplied audio tracks."""

        _require_non_blank("job_id", job_id)

        if target_duration_seconds <= 0:
            raise AudioProcessingError(
                "target_duration_seconds must be greater than zero"
            )

        if voice_asset.job_id != job_id:
            raise AudioProcessingError(
                "voice_asset job_id does not match requested job_id"
            )

        if voice_asset.media_type is not MediaType.VOICE:
            raise AudioProcessingError(
                "voice_asset must use MediaType.VOICE"
            )

        for asset in music_assets:
            self._validate_auxiliary_identity(
                job_id=job_id,
                asset=asset,
                expected_media_type=MediaType.MUSIC,
                role="music",
            )

        for asset in sound_effect_assets:
            self._validate_auxiliary_identity(
                job_id=job_id,
                asset=asset,
                expected_media_type=MediaType.SOUND_EFFECT,
                role="sound-effect",
            )

        voice_track = _load_verified_pcm_asset(voice_asset)
        sample_rate = voice_track.sample_rate

        target_frames = round(target_duration_seconds * sample_rate)

        if target_frames <= 0:
            raise AudioProcessingError(
                "target duration resolves to zero PCM frames"
            )

        output_root = Path(output_directory)
        output_root.mkdir(parents=True, exist_ok=True)

        processed_voice = self._prepare_asset(
            source_asset=voice_asset,
            track=voice_track,
            output_root=output_root,
            role="narration",
            target_frames=target_frames,
            required_sample_rate=sample_rate,
        )

        processed_music = tuple(
            self._prepare_asset(
                source_asset=asset,
                track=_load_verified_pcm_asset(asset),
                output_root=output_root,
                role=f"music-{index}",
                target_frames=target_frames,
                required_sample_rate=sample_rate,
            )
            for index, asset in enumerate(
                music_assets,
                start=1,
            )
        )

        processed_sfx = tuple(
            self._prepare_asset(
                source_asset=asset,
                track=_load_verified_pcm_asset(asset),
                output_root=output_root,
                role=f"sound-effect-{index}",
                target_frames=target_frames,
                required_sample_rate=sample_rate,
            )
            for index, asset in enumerate(
                sound_effect_assets,
                start=1,
            )
        )

        return AudioProcessingManifest(
            job_id=job_id,
            narration_asset=processed_voice,
            music_assets=processed_music,
            sound_effect_assets=processed_sfx,
            target_duration_seconds=target_duration_seconds,
            sample_rate=sample_rate,
        )

    def _validate_auxiliary_identity(
        self,
        *,
        job_id: str,
        asset: MediaAsset,
        expected_media_type: MediaType,
        role: str,
    ) -> None:
        if asset.job_id != job_id:
            raise AudioProcessingError(
                f"{role} asset job_id does not match requested job_id"
            )

        if asset.media_type is not expected_media_type:
            raise AudioProcessingError(
                f"{role} asset has incorrect media_type"
            )

    def _prepare_asset(
        self,
        *,
        source_asset: MediaAsset,
        track: _PcmTrack,
        output_root: Path,
        role: str,
        target_frames: int,
        required_sample_rate: int,
    ) -> MediaAsset:
        if track.sample_rate != required_sample_rate:
            raise AudioProcessingError(
                "all M15 audio tracks must use the narration sample rate"
            )

        cleaned = _remove_noise_floor_and_edge_silence(track.samples)
        normalized = _normalize_peak(cleaned)
        aligned = _align_duration(
            normalized,
            target_frames=target_frames,
        )

        identity_material = "\n".join(
            (
                f"source_asset_id={source_asset.asset_id}",
                f"source_checksum={source_asset.checksum_sha256}",
                f"role={role}",
                f"sample_rate={required_sample_rate}",
                f"target_frames={target_frames}",
                f"noise_gate={_NOISE_GATE_THRESHOLD}",
                f"target_peak={_TARGET_PEAK}",
            )
        )

        processing_id = sha256(
            identity_material.encode("utf-8")
        ).hexdigest()

        output_path = (
            output_root
            / f"m15-{role}-{processing_id[:20]}.wav"
        )

        _write_pcm_wav(
            path=output_path,
            sample_rate=required_sample_rate,
            samples=aligned,
        )

        body = _read_non_empty_file(output_path)
        checksum = sha256(body).hexdigest()

        asset_identity = (
            f"{source_asset.asset_id}\n{processing_id}\n{checksum}"
        )

        asset_id = (
            f"audio-{sha256(asset_identity.encode('utf-8')).hexdigest()[:24]}"
        )

        return MediaAsset(
            asset_id=asset_id,
            job_id=source_asset.job_id,
            media_type=source_asset.media_type,
            file_path=str(output_path.resolve()),
            checksum_sha256=checksum,
            provider_name=source_asset.provider_name,
            source_reference=(
                f"{source_asset.source_reference}#m15-audio-processed"
            ),
            validated=True,
        )


def _load_verified_pcm_asset(asset: MediaAsset) -> _PcmTrack:
    path = Path(asset.file_path)

    if not path.exists():
        raise AudioProcessingError(
            f"audio asset does not exist: {asset.asset_id}"
        )

    if not path.is_file():
        raise AudioProcessingError(
            f"audio asset path is not a file: {asset.asset_id}"
        )

    body = _read_non_empty_file(path)
    checksum = sha256(body).hexdigest()

    if checksum != asset.checksum_sha256:
        raise AudioProcessingError(
            f"audio asset checksum changed: {asset.asset_id}"
        )

    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            compression_type = wav_file.getcomptype()
            raw_frames = wav_file.readframes(frame_count)
    except (OSError, EOFError, wave.Error) as exc:
        raise AudioProcessingError(
            f"audio asset is not a readable WAV file: {asset.asset_id}"
        ) from exc

    if channels != _CHANNELS:
        raise AudioProcessingError(
            "M15 local audio preparation requires mono PCM WAV"
        )

    if sample_width != _SAMPLE_WIDTH_BYTES:
        raise AudioProcessingError(
            "M15 local audio preparation requires 16-bit PCM WAV"
        )

    if sample_rate <= 0:
        raise AudioProcessingError(
            "audio WAV sample rate must be greater than zero"
        )

    if frame_count <= 0:
        raise AudioProcessingError(
            "audio WAV must contain at least one frame"
        )

    if compression_type != "NONE":
        raise AudioProcessingError(
            "M15 local audio preparation requires uncompressed PCM WAV"
        )

    samples_array = array("h")
    samples_array.frombytes(raw_frames)

    if sys.byteorder != "little":
        samples_array.byteswap()

    samples = tuple(int(value) for value in samples_array)

    if len(samples) != frame_count:
        raise AudioProcessingError(
            "audio WAV frame count does not match decoded PCM samples"
        )

    return _PcmTrack(
        sample_rate=sample_rate,
        samples=samples,
    )


def _remove_noise_floor_and_edge_silence(
    samples: tuple[int, ...],
) -> tuple[int, ...]:
    gated = tuple(
        0 if abs(sample) <= _NOISE_GATE_THRESHOLD else sample
        for sample in samples
    )

    first_non_zero: int | None = None
    last_non_zero: int | None = None

    for index, sample in enumerate(gated):
        if sample != 0:
            first_non_zero = index
            break

    if first_non_zero is None:
        raise AudioProcessingError(
            "audio track contains no signal above the noise floor"
        )

    for index in range(len(gated) - 1, -1, -1):
        if gated[index] != 0:
            last_non_zero = index
            break

    if last_non_zero is None:
        raise AudioProcessingError(
            "audio track contains no signal above the noise floor"
        )

    return gated[first_non_zero : last_non_zero + 1]


def _normalize_peak(
    samples: tuple[int, ...],
) -> tuple[int, ...]:
    peak = max(abs(sample) for sample in samples)

    if peak <= 0:
        raise AudioProcessingError(
            "audio normalization requires non-zero signal"
        )

    scale = _TARGET_PEAK / peak

    normalized: list[int] = []

    for sample in samples:
        scaled = round(sample * scale)
        normalized.append(_clamp_int16(scaled))

    return tuple(normalized)


def _align_duration(
    samples: tuple[int, ...],
    *,
    target_frames: int,
) -> tuple[int, ...]:
    if target_frames <= 0:
        raise AudioProcessingError(
            "target_frames must be greater than zero"
        )

    if len(samples) >= target_frames:
        return samples[:target_frames]

    padding = (0,) * (target_frames - len(samples))

    return samples + padding


def _write_pcm_wav(
    *,
    path: Path,
    sample_rate: int,
    samples: tuple[int, ...],
) -> None:
    if sample_rate <= 0:
        raise AudioProcessingError(
            "sample_rate must be greater than zero"
        )

    if not samples:
        raise AudioProcessingError(
            "cannot write an empty PCM track"
        )

    path.parent.mkdir(parents=True, exist_ok=True)

    samples_array = array(
        "h",
        (_clamp_int16(sample) for sample in samples),
    )

    if sys.byteorder != "little":
        samples_array.byteswap()

    try:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(_CHANNELS)
            wav_file.setsampwidth(_SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_array.tobytes())
    except (OSError, wave.Error) as exc:
        raise AudioProcessingError(
            f"failed to write processed WAV: {path}"
        ) from exc


def _read_non_empty_file(path: Path) -> bytes:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise AudioProcessingError(
            f"audio file is unreadable: {path}"
        ) from exc

    if not body:
        raise AudioProcessingError(
            f"audio file must not be empty: {path}"
        )

    return body


def _clamp_int16(value: int) -> int:
    return max(-32_768, min(32_767, value))


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise AudioProcessingError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise AudioProcessingError(
            f"{name} must not contain surrounding whitespace"
        )
