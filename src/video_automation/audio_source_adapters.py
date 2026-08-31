"""Governed provider boundaries for ILAIOS Video Factory audio sourcing.

This module defines provider-neutral, fail-closed contracts for narration synthesis
and licensed music/SFX discovery. Concrete transports are injected by the existing
governed runtime; this module does not resolve credentials, select fallback
providers, or bypass policy/approval/evidence boundaries.

Runtime/provider E2E evidence is required before VERIFIED maturity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class AudioSourceError(ValueError):
    """Raised when governed audio-source data violates the contract."""


class TtsProvider(str, Enum):
    GEMINI = "gemini"


class AudioLibraryProvider(str, Enum):
    PIXABAY = "pixabay"


class AudioLibraryKind(str, Enum):
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"


@dataclass(frozen=True, slots=True)
class RateLimitState:
    remaining: int | None
    reset_at_iso8601: str | None

    def __post_init__(self) -> None:
        if self.remaining is not None and self.remaining < 0:
            raise AudioSourceError("rate-limit remaining must not be negative")
        if self.remaining == 0 and not self.reset_at_iso8601:
            raise AudioSourceError(
                "rate-limit reset time is required when remaining is zero"
            )


@dataclass(frozen=True, slots=True)
class TtsSynthesisRequest:
    tenant_id: str
    job_id: str
    provider: TtsProvider
    text: str
    voice_id: str
    language_code: str

    def __post_init__(self) -> None:
        _require_non_blank("tenant_id", self.tenant_id)
        _require_non_blank("job_id", self.job_id)
        _require_non_blank("text", self.text)
        _require_non_blank("voice_id", self.voice_id)
        _require_non_blank("language_code", self.language_code)


@dataclass(frozen=True, slots=True)
class TtsSynthesisResult:
    request: TtsSynthesisRequest
    audio_url: str
    mime_type: str
    provider_request_id: str
    retrieved_at_iso8601: str
    rate_limit: RateLimitState

    def __post_init__(self) -> None:
        _require_https_url("audio_url", self.audio_url)
        _require_non_blank("mime_type", self.mime_type)
        _require_non_blank("provider_request_id", self.provider_request_id)
        _require_non_blank("retrieved_at_iso8601", self.retrieved_at_iso8601)
        if not self.mime_type.startswith("audio/"):
            raise AudioSourceError("mime_type must be an audio media type")


@dataclass(frozen=True, slots=True)
class AudioLibrarySearchRequest:
    tenant_id: str
    job_id: str
    provider: AudioLibraryProvider
    kind: AudioLibraryKind
    query: str
    max_results: int = 10

    def __post_init__(self) -> None:
        _require_non_blank("tenant_id", self.tenant_id)
        _require_non_blank("job_id", self.job_id)
        _require_non_blank("query", self.query)
        if self.max_results < 1 or self.max_results > 50:
            raise AudioSourceError("max_results must be between 1 and 50")


@dataclass(frozen=True, slots=True)
class AudioSourceProvenance:
    provider: AudioLibraryProvider
    source_url: str
    asset_id: str
    creator: str | None
    license_name: str
    license_url: str | None
    attribution_required: bool
    retrieved_at_iso8601: str

    def __post_init__(self) -> None:
        _require_https_url("source_url", self.source_url)
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("license_name", self.license_name)
        _require_non_blank("retrieved_at_iso8601", self.retrieved_at_iso8601)
        if self.license_url is not None:
            _require_https_url("license_url", self.license_url)
        if self.attribution_required and not self.creator:
            raise AudioSourceError(
                "creator is required when attribution_required is true"
            )


@dataclass(frozen=True, slots=True)
class AudioLibraryCandidate:
    media_url: str
    preview_url: str | None
    duration_seconds: float | None
    kind: AudioLibraryKind
    provenance: AudioSourceProvenance

    def __post_init__(self) -> None:
        _require_https_url("media_url", self.media_url)
        if self.preview_url is not None:
            _require_https_url("preview_url", self.preview_url)
        if self.duration_seconds is not None and self.duration_seconds <= 0:
            raise AudioSourceError("duration_seconds must be positive when present")


@dataclass(frozen=True, slots=True)
class AudioLibrarySearchResult:
    request: AudioLibrarySearchRequest
    candidates: tuple[AudioLibraryCandidate, ...]
    rate_limit: RateLimitState

    def __post_init__(self) -> None:
        if len(self.candidates) > self.request.max_results:
            raise AudioSourceError("candidate count exceeds request max_results")
        for candidate in self.candidates:
            if candidate.provenance.provider is not self.request.provider:
                raise AudioSourceError(
                    "candidate provenance provider must match request provider"
                )
            if candidate.kind is not self.request.kind:
                raise AudioSourceError("candidate kind must match request kind")


class TtsTransport(Protocol):
    """Credential/network boundary supplied by the existing governed runtime."""

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
        """Execute one synthesis request and return validated provider metadata."""
        ...


class GovernedTtsAdapter(Protocol):
    provider: TtsProvider

    def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        """Return one validated synthesis result or fail closed."""
        ...


class GeminiTtsAdapter:
    provider = TtsProvider.GEMINI

    def __init__(self, transport: TtsTransport) -> None:
        self._transport = transport

    def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        if request.provider is not self.provider:
            raise AudioSourceError(
                f"{self.provider.value} adapter cannot execute "
                f"{request.provider.value} request"
            )
        result = self._transport.synthesize(
            provider=self.provider,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            text=request.text,
            voice_id=request.voice_id,
            language_code=request.language_code,
        )
        if result.request != request:
            raise AudioSourceError("transport result request must match adapter request")
        if result.request.provider is not self.provider:
            raise AudioSourceError("transport result provider must match adapter provider")
        return result


class AudioLibraryTransport(Protocol):
    """Credential/network boundary supplied by the existing governed runtime."""

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
        """Execute one library search and return licensed/provenanced candidates."""
        ...


class GovernedAudioLibraryAdapter(Protocol):
    provider: AudioLibraryProvider

    def search(self, request: AudioLibrarySearchRequest) -> AudioLibrarySearchResult:
        """Return validated candidates or fail closed; never silently fallback."""
        ...


class PixabayAudioLibraryAdapter:
    provider = AudioLibraryProvider.PIXABAY

    def __init__(self, transport: AudioLibraryTransport) -> None:
        self._transport = transport

    def search(self, request: AudioLibrarySearchRequest) -> AudioLibrarySearchResult:
        if request.provider is not self.provider:
            raise AudioSourceError(
                f"{self.provider.value} adapter cannot execute "
                f"{request.provider.value} request"
            )
        result = self._transport.search(
            provider=self.provider,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            kind=request.kind,
            query=request.query,
            max_results=request.max_results,
        )
        if result.request != request:
            raise AudioSourceError("transport result request must match adapter request")
        if result.request.provider is not self.provider:
            raise AudioSourceError("transport result provider must match adapter provider")
        return result


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise AudioSourceError(f"{name} must not be blank")
    if value != value.strip():
        raise AudioSourceError(f"{name} must not contain surrounding whitespace")


def _require_https_url(name: str, value: str) -> None:
    _require_non_blank(name, value)
    if not value.startswith("https://"):
        raise AudioSourceError(f"{name} must use https")
