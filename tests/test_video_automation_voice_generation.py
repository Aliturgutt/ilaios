"""Tests for canonical M14 Voice Generation."""

from __future__ import annotations

import wave
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.video_automation.models import (
    MediaType,
    ProviderRequest,
    ProviderResult,
)
from src.video_automation.provider_registry import ProviderRegistry
from src.video_automation.providers import (
    ProviderCapabilities,
    VoiceProvider,
)
from src.video_automation.voice_generation import (
    LocalTestVoiceProvider,
    VoiceGenerationCoordinator,
    VoiceGenerationError,
)


def _request(
    output_path: Path,
    *,
    provider_name: str = "local-test-voice",
    operation: str = "voice.generate",
    text: str = "Canonical local voice.",
) -> ProviderRequest:
    return ProviderRequest(
        request_id="voice-request-1",
        job_id="job-1",
        provider_name=provider_name,
        operation=operation,
        payload={
            "text": text,
            "output_path": str(output_path),
        },
    )


def test_local_provider_is_free_and_voice_capable() -> None:
    provider = LocalTestVoiceProvider()

    assert provider.capabilities.provider_name == "local-test-voice"
    assert provider.capabilities.operations == ("voice.generate",)
    assert provider.capabilities.is_paid is False
    assert provider.capabilities.metadata["execution_mode"] == "test"
    assert provider.capabilities.metadata["media_type"] == "voice"


def test_local_provider_registers_through_existing_registry() -> None:
    provider = LocalTestVoiceProvider()
    registry = ProviderRegistry((provider,))

    assert registry.get("local-test-voice") is provider

    assert registry.providers_supporting(
        "voice.generate",
        include_paid=False,
    ) == (provider,)


def test_local_provider_generates_valid_deterministic_pcm_wav() -> None:
    with TemporaryDirectory() as directory_name:
        output_path = Path(directory_name) / "voice.wav"
        provider = LocalTestVoiceProvider()

        first = provider.execute(_request(output_path))
        first_payload = output_path.read_bytes()

        second = provider.execute(_request(output_path))
        second_payload = output_path.read_bytes()

        assert first.success is True
        assert second.success is True
        assert first.external_id == second.external_id
        assert first_payload == second_payload

        assert (
            first.metadata["checksum_sha256"]
            == sha256(first_payload).hexdigest()
        )
        assert first.metadata["media_type"] == "voice"

        with wave.open(str(output_path), "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2
            assert wav_file.getframerate() == 16_000
            assert wav_file.getnframes() > 0


def test_local_provider_output_changes_with_text() -> None:
    with TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        provider = LocalTestVoiceProvider()

        first_path = directory / "first.wav"
        second_path = directory / "second.wav"

        first = provider.execute(
            _request(
                first_path,
                text="First narration.",
            )
        )
        second = provider.execute(
            _request(
                second_path,
                text="Second narration.",
            )
        )

        assert first.success is True
        assert second.success is True
        assert first_path.read_bytes() != second_path.read_bytes()


def test_local_provider_rejects_wrong_provider_name() -> None:
    with TemporaryDirectory() as directory_name:
        output_path = Path(directory_name) / "voice.wav"
        provider = LocalTestVoiceProvider()

        result = provider.execute(
            _request(
                output_path,
                provider_name="other-provider",
            )
        )

        assert result.success is False
        assert result.error_code == "invalid_request"


def test_local_provider_rejects_wrong_operation() -> None:
    with TemporaryDirectory() as directory_name:
        output_path = Path(directory_name) / "voice.wav"
        provider = LocalTestVoiceProvider()

        result = provider.execute(
            _request(
                output_path,
                operation="audio.normalize",
            )
        )

        assert result.success is False
        assert result.error_code == "invalid_request"


def test_local_provider_rejects_blank_text() -> None:
    with TemporaryDirectory() as directory_name:
        output_path = Path(directory_name) / "voice.wav"
        provider = LocalTestVoiceProvider()

        request = ProviderRequest(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="local-test-voice",
            operation="voice.generate",
            payload={
                "text": " ",
                "output_path": str(output_path),
            },
        )

        result = provider.execute(request)

        assert result.success is False
        assert result.error_code == "invalid_request"


def test_coordinator_requires_explicit_registered_provider() -> None:
    coordinator = VoiceGenerationCoordinator(ProviderRegistry())

    with TemporaryDirectory() as directory_name, pytest.raises(
        KeyError,
        match="provider not registered",
    ):
        coordinator.generate(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="local-test-voice",
            text="Narration.",
            output_path=Path(directory_name) / "voice.wav",
        )


def test_coordinator_normalizes_success_to_voice_media_asset() -> None:
    with TemporaryDirectory() as directory_name:
        output_path = Path(directory_name) / "voice.wav"

        provider = LocalTestVoiceProvider()
        coordinator = VoiceGenerationCoordinator(
            ProviderRegistry((provider,))
        )

        output = coordinator.generate(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="local-test-voice",
            text="Narration.",
            output_path=output_path,
        )

        assert output.provider_result.success is True
        assert output.asset is not None
        assert output.asset.job_id == "job-1"
        assert output.asset.media_type is MediaType.VOICE
        assert output.asset.provider_name == "local-test-voice"
        assert output.asset.file_path == str(output_path.resolve())
        assert output.asset.validated is False

        assert (
            output.asset.checksum_sha256
            == sha256(output_path.read_bytes()).hexdigest()
        )


def test_coordinator_uses_exact_explicit_provider() -> None:
    first = LocalTestVoiceProvider(provider_name="voice-a")
    second = LocalTestVoiceProvider(provider_name="voice-b")

    coordinator = VoiceGenerationCoordinator(
        ProviderRegistry((first, second))
    )

    with TemporaryDirectory() as directory_name:
        output = coordinator.generate(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="voice-b",
            text="Narration.",
            output_path=Path(directory_name) / "voice.wav",
        )

    assert output.provider_result.provider_name == "voice-b"
    assert output.asset is not None
    assert output.asset.provider_name == "voice-b"


class _FailingVoiceProvider(VoiceProvider):
    def __init__(self) -> None:
        super().__init__(
            ProviderCapabilities(
                provider_name="failing-voice",
                operations=("voice.generate",),
                is_paid=False,
            )
        )

    def execute(
        self,
        request: ProviderRequest,
    ) -> ProviderResult:
        self._validate_request(request)

        return ProviderResult(
            request_id=request.request_id,
            provider_name=request.provider_name,
            success=False,
            error_code="provider_failed",
            error_message="expected failure",
        )


def test_coordinator_preserves_provider_failure_without_asset() -> None:
    provider = _FailingVoiceProvider()

    coordinator = VoiceGenerationCoordinator(
        ProviderRegistry((provider,))
    )

    with TemporaryDirectory() as directory_name:
        output = coordinator.generate(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="failing-voice",
            text="Narration.",
            output_path=Path(directory_name) / "voice.wav",
        )

    assert output.provider_result.success is False
    assert output.provider_result.error_code == "provider_failed"
    assert output.asset is None


def test_coordinator_rejects_blank_text_before_execution() -> None:
    provider = LocalTestVoiceProvider()

    coordinator = VoiceGenerationCoordinator(
        ProviderRegistry((provider,))
    )

    with TemporaryDirectory() as directory_name, pytest.raises(
        VoiceGenerationError,
        match="text",
    ):
        coordinator.generate(
            request_id="voice-request-1",
            job_id="job-1",
            provider_name="local-test-voice",
            text=" ",
            output_path=Path(directory_name) / "voice.wav",
        )
