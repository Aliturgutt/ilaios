"""OAuth-reference-bound YouTube, TikTok, and Instagram publishing adapters.

The adapters implement the existing PlatformPublisher contract and delegate one
external side effect to an injected transport. OAuth access tokens are never
stored here; the transport resolves the server-side authorization reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.video_automation.publishing_execution import (
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class SocialPublishingAdapterError(ValueError):
    """Raised before transport dispatch when platform/account authority mismatches."""


@dataclass(frozen=True, slots=True)
class SocialPublishTransportResult:
    succeeded: bool
    provider_name: str
    platform_post_id: str | None = None
    published_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _text("provider_name", self.provider_name)
        if self.succeeded:
            if self.platform_post_id is None:
                raise SocialPublishingAdapterError(
                    "successful social publish transport result requires platform_post_id"
                )
            _text("platform_post_id", self.platform_post_id)
            if self.published_url is not None:
                _text("published_url", self.published_url)
            if self.error_code is not None or self.error_message is not None:
                raise SocialPublishingAdapterError(
                    "successful social publish transport result must not contain errors"
                )
        else:
            if self.error_message is None:
                raise SocialPublishingAdapterError(
                    "failed social publish transport result requires error_message"
                )
            _text("error_message", self.error_message)
            if self.error_code is not None:
                _text("error_code", self.error_code)
            if self.platform_post_id is not None or self.published_url is not None:
                raise SocialPublishingAdapterError(
                    "failed social publish transport result cannot contain publication identity"
                )


class SocialPublishTransport(Protocol):
    """Server-side external transport; implementations resolve OAuth references securely."""

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult: ...


class OAuthBoundSocialPublisher:
    """One-account publisher adapter with no retry and no credential material."""

    def __init__(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        required_oauth_scopes: tuple[str, ...],
        transport: SocialPublishTransport,
    ) -> None:
        normalized = platform.strip().lower()
        _text("platform", normalized)
        _text("account_id", account_id)
        _text("oauth_authorization_ref", oauth_authorization_ref)
        if not required_oauth_scopes:
            raise SocialPublishingAdapterError("required_oauth_scopes must not be empty")
        if len(required_oauth_scopes) != len(set(required_oauth_scopes)):
            raise SocialPublishingAdapterError("required OAuth scopes must be unique")
        for scope in required_oauth_scopes:
            _text("required OAuth scope", scope)
        self._platform = normalized
        self._account_id = account_id
        self._oauth_authorization_ref = oauth_authorization_ref
        self._required_oauth_scopes = required_oauth_scopes
        self._transport = transport

    @property
    def publisher_id(self) -> str:
        return f"oauth-social-publisher:{self._platform}:{self._account_id}"

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def oauth_authorization_ref(self) -> str:
        return self._oauth_authorization_ref

    @property
    def required_oauth_scopes(self) -> tuple[str, ...]:
        return self._required_oauth_scopes

    def publish(self, package: PlatformPublishingPackage) -> PlatformPublishingObservation:
        if package.platform != self._platform:
            raise SocialPublishingAdapterError("package platform does not match adapter")
        if package.account_id != self._account_id:
            raise SocialPublishingAdapterError("package account does not match adapter")
        result = self._transport.publish(
            platform=self._platform,
            account_id=self._account_id,
            oauth_authorization_ref=self._oauth_authorization_ref,
            package=package,
        )
        if result.succeeded:
            return PlatformPublishingObservation(
                package_id=package.package_id,
                platform=package.platform,
                account_id=package.account_id,
                status=PublishingExecutionStatus.SUCCEEDED,
                provider_name=result.provider_name,
                platform_post_id=result.platform_post_id,
                published_url=result.published_url,
                metadata={"publisher_id": self.publisher_id},
            )
        return PlatformPublishingObservation(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            status=PublishingExecutionStatus.FAILED,
            provider_name=result.provider_name,
            error_code=result.error_code,
            error_message=result.error_message,
            metadata={"publisher_id": self.publisher_id},
        )


class YouTubePublisherAdapter(OAuthBoundSocialPublisher):
    def __init__(
        self,
        *,
        account_id: str,
        oauth_authorization_ref: str,
        required_oauth_scopes: tuple[str, ...],
        transport: SocialPublishTransport,
    ) -> None:
        super().__init__(
            platform="youtube",
            account_id=account_id,
            oauth_authorization_ref=oauth_authorization_ref,
            required_oauth_scopes=required_oauth_scopes,
            transport=transport,
        )


class TikTokPublisherAdapter(OAuthBoundSocialPublisher):
    def __init__(
        self,
        *,
        account_id: str,
        oauth_authorization_ref: str,
        required_oauth_scopes: tuple[str, ...],
        transport: SocialPublishTransport,
    ) -> None:
        super().__init__(
            platform="tiktok",
            account_id=account_id,
            oauth_authorization_ref=oauth_authorization_ref,
            required_oauth_scopes=required_oauth_scopes,
            transport=transport,
        )


class InstagramPublisherAdapter(OAuthBoundSocialPublisher):
    def __init__(
        self,
        *,
        account_id: str,
        oauth_authorization_ref: str,
        required_oauth_scopes: tuple[str, ...],
        transport: SocialPublishTransport,
    ) -> None:
        super().__init__(
            platform="instagram",
            account_id=account_id,
            oauth_authorization_ref=oauth_authorization_ref,
            required_oauth_scopes=required_oauth_scopes,
            transport=transport,
        )


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise SocialPublishingAdapterError(f"{name} must be non-blank normalized text")
