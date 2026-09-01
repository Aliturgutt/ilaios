"""Canonical M14 voice generation for ILAIOS Video Automation.

This module binds the existing VoiceProvider contract to one explicit,
provider-neutral coordinator and provides a deterministic local/free TEST MODE
implementation.

Audio processing, normalization, alignment, mixing, captions, and
transcription are intentionally outside M14.
"""

from __future__ import annotations

import math
import struct
import wave
from hashlib import sha256
from pathlib import Path

from .models import MediaAsset, MediaType, ProviderRequest, ProviderResult
from .provider_registry import ProviderRegistry
from .providers import MediaProviderOutput, ProviderCapabilities, VoiceProvider

_DEFAULT_PROVIDER_NAME = "local-test-voice"
_DEFAULT_OPERATION = "voice.generate"
_SAMPLE_RATE = 16_000
_SAMPLE_WIDTH_BYTES = 2
_CHANNELS = 1


class VoiceGenerationError(ValueError):
    """Raised when canonical M14 voice generation cannot proceed safely."""


class LocalTestVoiceProvider(VoiceProvider):
    """Generate a deterministic local PCM WAV placeholder for TEST MODE."""

    def __init__(
        self,
        *,
        provider_name: str = _DEFAULT_PROVIDER_NAME,
    ) -> None:
        _require_non_blank("provider_name", provider_name)

        super().__init__(
            ProviderCapabilities(
                provider_name=provider_name,
                operations=(_DEFAULT_OPERATION,),
                is_paid=False,
                metadata={
                    "execution_mode": "test",
                    "media_type": "voice",
                    "source": "local_generated_wav",
                },
            )
        )

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Generate one deterministic mono PCM WAV without network access."""

        try:
            self._validate_request(request)
        except ValueError as exc:
            return _failure(
                request,
                error_code="invalid_request",
                message=str(exc),
            )

        text = request.payload.get("text")
        output_path_value = request.payload.get("output_path")

        if not isinstance(text, str):
            return _failure(
                request,
                error_code="invalid_request",
                message="payload text must be a string",
            )

        if not text or not text.strip() or text != text.strip():
            return _failure(
                request,
                error_code="invalid_request",
                message=(
                    "payload text must be non-blank without surrounding "
                    "whitespace"
                ),
            )

        if not isinstance(output_path_value, str):
            return _failure(
                request,
                error_code="invalid_request",
                message="payload output_path must be a string",
            )

        if (
            not output_path_value
            or not output_path_value.strip()
            or output_path_value != output_path_value.strip()
        ):
            return _failure(
                request,
                error_code="invalid_request",
                message=(
                    "payload output_path must be non-blank without "
                    "surrounding whitespace"
                ),
            )

        output_path = Path(output_path_value)

        if output_path.suffix.lower() != ".wav":
            return _failure(
                request,
                error_code="invalid_request",
                message="payload output_path must use .wav extension",
            )

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _write_placeholder_wav(output_path, text)
            payload = output_path.read_bytes()
        except (OSError, wave.Error) as exc:
            return _failure(
                request,
                error_code="local_generation_failed",
                message=f"failed to generate local voice track: {exc}",
            )

        checksum = sha256(payload).hexdigest()

        identity_material = "\n".join(
            (
                f"request_id={request.request_id}",
                f"job_id={request.job_id}",
                f"text_sha256={sha256(text.encode('utf-8')).hexdigest()}",
                f"wav_sha256={checksum}",
            )
        )
        identity_sha256 = sha256(
            identity_material.encode("utf-8")
        ).hexdigest()

        resolved_path = output_path.resolve()

        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id=f"local-voice-{identity_sha256[:24]}",
            metadata={
                "asset_path": str(resolved_path),
                "checksum_sha256": checksum,
                "execution_mode": "test",
                "media_type": "voice",
                "source_reference": f"local://{resolved_path.name}",
            },
        )


class VoiceGenerationCoordinator:
    """Generate voice through an explicitly selected VoiceProvider."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def generate(
        self,
        *,
        request_id: str,
        job_id: str,
        provider_name: str,
        text: str,
        output_path: str | Path,
    ) -> MediaProviderOutput:
        """Run voice.generate and normalize success into MediaAsset."""

        for name, value in (
            ("request_id", request_id),
            ("job_id", job_id),
            ("provider_name", provider_name),
            ("text", text),
        ):
            _require_non_blank(name, value)

        provider = self._registry.get(provider_name)

        if not isinstance(provider, VoiceProvider):
            raise VoiceGenerationError(
                "registered provider is not a VoiceProvider: "
                f"{provider_name}"
            )

        if not provider.capabilities.supports(_DEFAULT_OPERATION):
            raise VoiceGenerationError(
                "voice provider does not support "
                f"{_DEFAULT_OPERATION}: {provider_name}"
            )

        path = Path(output_path)

        request = ProviderRequest(
            request_id=request_id,
            job_id=job_id,
            provider_name=provider_name,
            operation=_DEFAULT_OPERATION,
            payload={
                "text": text,
                "output_path": str(path),
            },
        )

        result = provider.execute(request)

        if not result.success:
            return MediaProviderOutput(
                provider_result=result,
                asset=None,
            )

        asset_path_value = result.metadata.get("asset_path")
        checksum_value = result.metadata.get("checksum_sha256")
        source_reference_value = result.metadata.get("source_reference")

        if not isinstance(asset_path_value, str):
            raise VoiceGenerationError(
                "successful voice provider result requires string asset_path"
            )

        if not isinstance(checksum_value, str):
            raise VoiceGenerationError(
                "successful voice provider result requires string "
                "checksum_sha256"
            )

        if not isinstance(source_reference_value, str):
            raise VoiceGenerationError(
                "successful voice provider result requires string "
                "source_reference"
            )

        asset_path = Path(asset_path_value)

        try:
            payload = asset_path.read_bytes()
        except OSError as exc:
            raise VoiceGenerationError(
                "successful voice provider asset is unreadable: "
                f"{asset_path}"
            ) from exc

        actual_checksum = sha256(payload).hexdigest()

        if actual_checksum != checksum_value:
            raise VoiceGenerationError(
                "successful voice provider checksum does not match "
                "asset bytes"
            )

        identity_material = "\n".join(
            (
                f"job_id={job_id}",
                f"request_id={request_id}",
                f"provider_name={provider_name}",
                f"checksum_sha256={checksum_value}",
            )
        )

        asset_id = (
            "voice-"
            + sha256(identity_material.encode("utf-8")).hexdigest()[:24]
        )

        asset = MediaAsset(
            asset_id=asset_id,
            job_id=job_id,
            media_type=MediaType.VOICE,
            file_path=str(asset_path.resolve()),
            checksum_sha256=checksum_value,
            provider_name=provider_name,
            source_reference=source_reference_value,
            validated=False,
        )

        return MediaProviderOutput(
            provider_result=result,
            asset=asset,
        )


def _write_placeholder_wav(path: Path, text: str) -> None:
    """Write deterministic placeholder audio derived from narration text."""

    text_bytes = text.encode("utf-8")
    text_digest = sha256(text_bytes).digest()

    duration_seconds = max(
        0.5,
        len(text_bytes) / 24.0,
    )
    frame_count = int(_SAMPLE_RATE * duration_seconds)

    amplitude = 4_000
    base_frequency = 180 + text_digest[0]
    frames = bytearray()

    for index in range(frame_count):
        second_frequency = 90 + text_digest[index % len(text_digest)]

        sample = int(
            amplitude
            * (
                0.65
                * math.sin(
                    2.0
                    * math.pi
                    * base_frequency
                    * index
                    / _SAMPLE_RATE
                )
                + 0.35
                * math.sin(
                    2.0
                    * math.pi
                    * second_frequency
                    * index
                    / _SAMPLE_RATE
                )
            )
        )

        frames.extend(struct.pack("<h", sample))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(_CHANNELS)
        wav_file.setsampwidth(_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(_SAMPLE_RATE)
        wav_file.writeframes(bytes(frames))


def _failure(
    request: ProviderRequest,
    *,
    error_code: str,
    message: str,
) -> ProviderResult:
    return ProviderResult(
        request_id=request.request_id,
        provider_name=request.provider_name,
        success=False,
        error_code=error_code,
        error_message=message,
    )


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise VoiceGenerationError(f"{name} must not be blank")

    if value != value.strip():
        raise VoiceGenerationError(
            f"{name} must not contain surrounding whitespace"
        )
