"""Platform publisher adapters with injected OAuth-aware transports.

OAuth tokens/secrets are never stored in packages or adapter objects. The adapter
receives only an opaque authorization reference resolved by the server-side
transport implementation at execution time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from .publishing_package_preparation import PlatformPublishingPackage


class PlatformPublisherAdapterError(RuntimeError):
    """Raised when a governed social publishing adapter is misconfigured."""


@dataclass(frozen=True, slots=True)
class PlatformPublishRequest:
    platform: str
    authorization_reference: str
    package_id: str
    account_id: str
    media_path: str
    media_sha256_hex: str
    title: str
    description: str
    tags: tuple[str, ...]
    visibility: str


@dataclass(frozen=True, slots=True)
class PlatformPublishResponse:
    platform_post_id: str
    published_url: str | None = None

    def __post_init__(self) -> None:
        _text("platform_post_id", self.platform_post_id)
        if self.published_url is not None:
            _text("published_url", self.published_url)


class OAuthPublishingTransport(Protocol):
    """Server-side transport that resolves opaque OAuth authorization references."""

    def publish(self, request: PlatformPublishRequest) -> PlatformPublishResponse: ...


class OAuthPlatformPublisher:
    """Explicit platform adapter; selection remains outside this class."""

    PLATFORM = ""
    PUBLISHER_ID = ""

    def __init__(
        self,
        *,
        authorization_reference: str,
        transport: OAuthPublishingTransport,
    ) -> None:
        self._authorization_reference = _text(
            "authorization_reference", authorization_reference
        )
        self._transport = transport
        if not self.PLATFORM or not self.PUBLISHER_ID:
            raise PlatformPublisherAdapterError("platform adapter constants are missing")

    @property
    def publisher_id(self) -> str:
        return self.PUBLISHER_ID

    @property
    def platform(self) -> str:
        return self.PLATFORM

    def publish(
        self,
        package: PlatformPublishingPackage,
    ) -> PlatformPublishingObservation:
        if package.platform != self.PLATFORM:
            raise PlatformPublisherAdapterError(
                "publishing package platform does not match adapter"
            )
        response = self._transport.publish(
            PlatformPublishRequest(
                platform=self.PLATFORM,
                authorization_reference=self._authorization_reference,
                package_id=package.package_id,
                account_id=package.account_id,
                media_path=package.media_path,
                media_sha256_hex=package.media_sha256_hex,
                title=package.title,
                description=package.description,
                tags=package.tags,
                visibility=package.visibility,
            )
        )
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.SUCCEEDED,
            provider_name=self.PUBLISHER_ID,
            platform_post_id=response.platform_post_id,
            published_url=response.published_url,
            metadata={"oauth_authorization": "server-resolved"},
        )


class YouTubePublisher(OAuthPlatformPublisher):
    PLATFORM = "youtube"
    PUBLISHER_ID = "ilaios.youtube.oauth"


class TikTokPublisher(OAuthPlatformPublisher):
    PLATFORM = "tiktok"
    PUBLISHER_ID = "ilaios.tiktok.oauth"


class InstagramPublisher(OAuthPlatformPublisher):
    PLATFORM = "instagram"
    PUBLISHER_ID = "ilaios.instagram.oauth"


def _text(name: str, value: str) -> str:
    if not value or value != value.strip():
        raise PlatformPublisherAdapterError(f"{name} must be non-blank and trimmed")
    return value
