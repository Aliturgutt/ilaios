from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.video_automation.audio_source_adapters import (
    AudioLibraryCandidate,
    AudioLibraryKind,
    AudioLibraryProvider,
    AudioLibrarySearchRequest,
    AudioLibrarySearchResult,
    AudioLibraryTransport,
    AudioSourceError,
    AudioSourceProvenance,
    GeminiTtsAdapter,
    PixabayAudioLibraryAdapter,
    RateLimitState,
    TtsProvider,
    TtsSynthesisRequest,
    TtsSynthesisResult,
    TtsTransport,
)


def _tts_request() -> TtsSynthesisRequest:
    return TtsSynthesisRequest(
        tenant_id="tenant-1",
        job_id="job-1",
        provider=TtsProvider.GEMINI,
        text="Narration text",
        voice_id="voice-1",
        language_code="en-US",
    )


@dataclass
class _FakeTtsTransport:
    request_override: TtsSynthesisRequest | None = None

    def synthesize(
        self,
        *,
        provider: TtsProvider,
        tenant_id: str,
        job_id: str,
        text: str,
        voice_id: str,
        language_code: str,
    ) -> TtsSynthesisResult:
        request = self.request_override or TtsSynthesisRequest(
            tenant_id=tenant_id,
            job_id=job_id,
            provider=provider,
            text=text,
            voice_id=voice_id,
            language_code=language_code,
        )
        return TtsSynthesisResult(
            request=request,
            audio_url="https://example.test/narration.wav",
            mime_type="audio/wav",
            provider_request_id="req-1",
            retrieved_at_iso8601="2026-08-31T02:20:00Z",
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def _library_request(kind: AudioLibraryKind) -> AudioLibrarySearchRequest:
    return AudioLibrarySearchRequest(
        tenant_id="tenant-1",
        job_id="job-1",
        provider=AudioLibraryProvider.PIXABAY,
        kind=kind,
        query="cinematic pulse",
        max_results=10,
    )


def _candidate(kind: AudioLibraryKind) -> AudioLibraryCandidate:
    return AudioLibraryCandidate(
        media_url="https://example.test/audio.mp3",
        preview_url="https://example.test/preview.mp3",
        duration_seconds=12.5,
        kind=kind,
        provenance=AudioSourceProvenance(
            provider=AudioLibraryProvider.PIXABAY,
            source_url="https://example.test/source/1",
            asset_id="asset-1",
            creator="creator",
            license_name="provider-license",
            license_url="https://example.test/license",
            attribution_required=True,
            retrieved_at_iso8601="2026-08-31T02:20:00Z",
        ),
    )


@dataclass
class _FakeLibraryTransport:
    request_override: AudioLibrarySearchRequest | None = None

    def search(
        self,
        *,
        provider: AudioLibraryProvider,
        tenant_id: str,
        job_id: str,
        kind: AudioLibraryKind,
        query: str,
        max_results: int,
    ) -> AudioLibrarySearchResult:
        request = self.request_override or AudioLibrarySearchRequest(
            tenant_id=tenant_id,
            job_id=job_id,
            provider=provider,
            kind=kind,
            query=query,
            max_results=max_results,
        )
        return AudioLibrarySearchResult(
            request=request,
            candidates=(_candidate(kind),),
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_tts_result_requires_audio_https_url() -> None:
    request = _tts_request()
    with pytest.raises(AudioSourceError, match="audio_url must use https"):
        TtsSynthesisResult(
            request=request,
            audio_url="http://example.test/narration.wav",
            mime_type="audio/wav",
            provider_request_id="req-1",
            retrieved_at_iso8601="2026-08-31T02:20:00Z",
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_tts_adapter_rejects_transport_request_substitution() -> None:
    original = _tts_request()
    substituted = TtsSynthesisRequest(
        tenant_id="other-tenant",
        job_id="job-1",
        provider=TtsProvider.GEMINI,
        text="Narration text",
        voice_id="voice-1",
        language_code="en-US",
    )
    adapter = GeminiTtsAdapter(_FakeTtsTransport(request_override=substituted))
    with pytest.raises(AudioSourceError, match="must match adapter request"):
        adapter.synthesize(original)


def test_tts_adapter_preserves_governed_request() -> None:
    request = _tts_request()
    transport: TtsTransport = _FakeTtsTransport()
    result = GeminiTtsAdapter(transport).synthesize(request)
    assert result.request == request
    assert result.request.provider is TtsProvider.GEMINI
    assert result.mime_type == "audio/wav"


def test_audio_library_requires_license_metadata() -> None:
    with pytest.raises(AudioSourceError, match="license_name must not be blank"):
        AudioSourceProvenance(
            provider=AudioLibraryProvider.PIXABAY,
            source_url="https://example.test/source/1",
            asset_id="asset-1",
            creator=None,
            license_name="",
            license_url=None,
            attribution_required=False,
            retrieved_at_iso8601="2026-08-31T02:20:00Z",
        )


def test_audio_library_rejects_kind_mismatch() -> None:
    request = _library_request(AudioLibraryKind.MUSIC)
    with pytest.raises(AudioSourceError, match="candidate kind must match"):
        AudioLibrarySearchResult(
            request=request,
            candidates=(_candidate(AudioLibraryKind.SOUND_EFFECT),),
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_audio_library_adapter_preserves_music_provenance() -> None:
    request = _library_request(AudioLibraryKind.MUSIC)
    transport: AudioLibraryTransport = _FakeLibraryTransport()
    result = PixabayAudioLibraryAdapter(transport).search(request)
    assert result.request == request
    assert result.candidates[0].kind is AudioLibraryKind.MUSIC
    assert result.candidates[0].provenance.license_name == "provider-license"


def test_audio_library_adapter_preserves_sfx_provenance() -> None:
    request = _library_request(AudioLibraryKind.SOUND_EFFECT)
    result = PixabayAudioLibraryAdapter(_FakeLibraryTransport()).search(request)
    assert result.request == request
    assert result.candidates[0].kind is AudioLibraryKind.SOUND_EFFECT
    assert result.candidates[0].provenance.provider is AudioLibraryProvider.PIXABAY


def test_rate_limit_exhaustion_requires_reset_time() -> None:
    with pytest.raises(AudioSourceError, match="reset time is required"):
        RateLimitState(remaining=0, reset_at_iso8601=None)
