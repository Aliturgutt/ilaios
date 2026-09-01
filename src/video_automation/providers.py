"""Provider-independent interfaces for ILAIOS Video Automation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from .models import (
    MediaAsset,
    ProviderRequest,
    ProviderResult,
    RenderArtifact,
)

MetadataValue = str | int | float | bool | None


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


def _freeze_metadata(
    metadata: Mapping[str, MetadataValue],
) -> Mapping[str, MetadataValue]:
    normalized: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        _validate_text("metadata key", key)
        normalized[key] = value
    return MappingProxyType(dict(sorted(normalized.items())))


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Static capabilities advertised by one provider implementation."""

    provider_name: str
    operations: tuple[str, ...]
    is_paid: bool
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_text("provider_name", self.provider_name)
        if not self.operations:
            raise ValueError("operations must not be empty")

        seen: set[str] = set()
        for operation in self.operations:
            _validate_text("operation", operation)
            if operation in seen:
                raise ValueError(f"duplicate operation: {operation}")
            seen.add(operation)

        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    def supports(self, operation: str) -> bool:
        _validate_text("operation", operation)
        return operation in self.operations


@runtime_checkable
class Provider(Protocol):
    """Minimal provider contract used by registries and selectors."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return immutable provider capabilities."""

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one provider-neutral request."""


class BaseProvider(ABC):
    """Shared provider base class with capability validation."""

    def __init__(self, capabilities: ProviderCapabilities) -> None:
        self._capabilities = capabilities

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _validate_request(self, request: ProviderRequest) -> None:
        if request.provider_name != self.capabilities.provider_name:
            raise ValueError(
                "request provider_name does not match provider capabilities"
            )
        if not self.capabilities.supports(request.operation):
            raise ValueError(
                f"provider does not support operation: {request.operation}"
            )

    @abstractmethod
    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Execute one provider-neutral request."""


class VideoGenerationProvider(BaseProvider, ABC):
    """Provider contract for generated video assets."""


class ImageGenerationProvider(BaseProvider, ABC):
    """Provider contract for generated image assets."""


class StockMediaProvider(BaseProvider, ABC):
    """Provider contract for acquired stock media assets."""


class VoiceProvider(BaseProvider, ABC):
    """Provider contract for voice/TTS generation."""


class MusicProvider(BaseProvider, ABC):
    """Provider contract for music generation or acquisition."""


class SoundEffectProvider(BaseProvider, ABC):
    """Provider contract for sound-effect generation or acquisition."""


class TranscriptionProvider(BaseProvider, ABC):
    """Provider contract for transcription/caption source generation."""


class PublishingProvider(BaseProvider, ABC):
    """Provider contract for social publishing operations."""


@dataclass(frozen=True, slots=True)
class MediaProviderOutput:
    """Normalized media result returned by media-oriented providers."""

    provider_result: ProviderResult
    asset: MediaAsset | None

    def __post_init__(self) -> None:
        if self.provider_result.success and self.asset is None:
            raise ValueError("successful media provider output requires an asset")
        if not self.provider_result.success and self.asset is not None:
            raise ValueError("failed media provider output must not contain an asset")


@dataclass(frozen=True, slots=True)
class PublishingProviderOutput:
    """Normalized publishing result."""

    provider_result: ProviderResult
    platform_post_id: str | None = None
    published_url: str | None = None

    def __post_init__(self) -> None:
        if self.platform_post_id is not None:
            _validate_text("platform_post_id", self.platform_post_id)
        if self.published_url is not None:
            _validate_text("published_url", self.published_url)

        if self.provider_result.success:
            if self.platform_post_id is None:
                raise ValueError(
                    "successful publishing output requires platform_post_id"
                )
        else:
            if self.platform_post_id is not None or self.published_url is not None:
                raise ValueError(
                    "failed publishing output must not contain publication identifiers"
                )


@dataclass(frozen=True, slots=True)
class RenderProviderOutput:
    """Normalized result for provider-backed rendering operations."""

    provider_result: ProviderResult
    artifact: RenderArtifact | None

    def __post_init__(self) -> None:
        if self.provider_result.success and self.artifact is None:
            raise ValueError("successful render provider output requires artifact")
        if not self.provider_result.success and self.artifact is not None:
            raise ValueError("failed render provider output must not contain artifact")
