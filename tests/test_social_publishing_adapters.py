from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from services.integrations.social_publishing import (
    InstagramPublisherAdapter,
    SocialPublishingAdapterError,
    SocialPublishTransportResult,
    TikTokPublisherAdapter,
    YouTubePublisherAdapter,
)
from src.video_automation.publishing_execution import PublishingExecutionStatus
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


@dataclass
class _Transport:
    result: SocialPublishTransportResult
    calls: int = 0
    observed_platform: str | None = None
    observed_account_id: str | None = None
    observed_oauth_ref: str | None = None

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult:
        del package
        self.calls += 1
        self.observed_platform = platform
        self.observed_account_id = account_id
        self.observed_oauth_ref = oauth_authorization_ref
        return self.result


def _package(*, platform: str, account_id: str) -> PlatformPublishingPackage:
    return PlatformPublishingPackage(
        package_id=f"package-{platform}",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform=platform,
        account_id=account_id,
        media_path="/tmp/final.mp4",
        media_sha256_hex="a" * 64,
        media_byte_length=100,
        scheduled_at=datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc),
        visibility="private",
        title="Title",
        description="Description",
        tags=("ilaios",),
    )


def _success() -> SocialPublishTransportResult:
    return SocialPublishTransportResult(
        succeeded=True,
        provider_name="social-api",
        platform_post_id="post-001",
        published_url="https://example.invalid/post-001",
    )


def test_youtube_adapter_delegates_one_call_with_oauth_reference_only() -> None:
    transport = _Transport(_success())
    publisher = YouTubePublisherAdapter(
        account_id="youtube-account",
        oauth_authorization_ref="oauth://youtube/account",
        required_oauth_scopes=("scope-from-current-oauth-config",),
        transport=transport,
    )

    observation = publisher.publish(
        _package(platform="youtube", account_id="youtube-account")
    )

    assert observation.status is PublishingExecutionStatus.SUCCEEDED
    assert observation.platform_post_id == "post-001"
    assert transport.calls == 1
    assert transport.observed_platform == "youtube"
    assert transport.observed_account_id == "youtube-account"
    assert transport.observed_oauth_ref == "oauth://youtube/account"


def test_tiktok_and_instagram_adapters_bind_exact_platforms() -> None:
    tiktok_transport = _Transport(_success())
    instagram_transport = _Transport(_success())
    tiktok = TikTokPublisherAdapter(
        account_id="tiktok-account",
        oauth_authorization_ref="oauth://tiktok/account",
        required_oauth_scopes=("scope-from-current-oauth-config",),
        transport=tiktok_transport,
    )
    instagram = InstagramPublisherAdapter(
        account_id="instagram-account",
        oauth_authorization_ref="oauth://instagram/account",
        required_oauth_scopes=("scope-from-current-oauth-config",),
        transport=instagram_transport,
    )

    assert tiktok.publish(
        _package(platform="tiktok", account_id="tiktok-account")
    ).status is PublishingExecutionStatus.SUCCEEDED
    assert instagram.publish(
        _package(platform="instagram", account_id="instagram-account")
    ).status is PublishingExecutionStatus.SUCCEEDED
    assert tiktok_transport.observed_platform == "tiktok"
    assert instagram_transport.observed_platform == "instagram"


def test_adapter_account_mismatch_blocks_before_transport() -> None:
    transport = _Transport(_success())
    publisher = YouTubePublisherAdapter(
        account_id="authorized-account",
        oauth_authorization_ref="oauth://youtube/authorized",
        required_oauth_scopes=("scope-from-current-oauth-config",),
        transport=transport,
    )

    with pytest.raises(SocialPublishingAdapterError, match="account does not match"):
        publisher.publish(_package(platform="youtube", account_id="wrong-account"))

    assert transport.calls == 0


def test_explicit_transport_failure_is_normalized_without_retry() -> None:
    transport = _Transport(
        SocialPublishTransportResult(
            succeeded=False,
            provider_name="social-api",
            error_code="oauth_expired",
            error_message="authorization expired",
        )
    )
    publisher = InstagramPublisherAdapter(
        account_id="instagram-account",
        oauth_authorization_ref="oauth://instagram/account",
        required_oauth_scopes=("scope-from-current-oauth-config",),
        transport=transport,
    )

    observation = publisher.publish(
        _package(platform="instagram", account_id="instagram-account")
    )

    assert observation.status is PublishingExecutionStatus.FAILED
    assert observation.error_code == "oauth_expired"
    assert transport.calls == 1
