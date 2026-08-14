from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.video_automation.platform_publishers import (
    InstagramPublisher,
    PlatformPublishRequest,
    PlatformPublishResponse,
    PlatformPublisherAdapterError,
    TikTokPublisher,
    YouTubePublisher,
)
from src.video_automation.publishing_execution import PublishingExecutionStatus
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class _Transport:
    def __init__(self) -> None:
        self.requests: list[PlatformPublishRequest] = []

    def publish(self, request: PlatformPublishRequest) -> PlatformPublishResponse:
        self.requests.append(request)
        return PlatformPublishResponse(
            platform_post_id=f"{request.platform}-post-001",
            published_url=f"https://example.invalid/{request.platform}/post-001",
        )


def _package(platform: str) -> PlatformPublishingPackage:
    return PlatformPublishingPackage(
        package_id=f"package-{platform}-001",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform=platform,
        account_id="account-001",
        media_path="/tmp/final.mp4",
        media_sha256_hex="a" * 64,
        media_byte_length=1234,
        scheduled_at=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        visibility="public",
        title="Episode 1",
        description="Description",
        tags=("ilaios",),
    )


@pytest.mark.parametrize(
    ("publisher_type", "platform"),
    (
        (YouTubePublisher, "youtube"),
        (TikTokPublisher, "tiktok"),
        (InstagramPublisher, "instagram"),
    ),
)
def test_platform_adapter_uses_opaque_oauth_reference_and_exact_artifact(
    publisher_type, platform: str
) -> None:
    transport = _Transport()
    publisher = publisher_type(
        authorization_reference="oauth-ref-account-001",
        transport=transport,
    )
    observation = publisher.publish(_package(platform))

    assert observation.status is PublishingExecutionStatus.SUCCEEDED
    assert observation.platform_post_id == f"{platform}-post-001"
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.authorization_reference == "oauth-ref-account-001"
    assert request.media_sha256_hex == "a" * 64
    assert "token" not in request.authorization_reference.lower()


def test_platform_adapter_rejects_cross_platform_package() -> None:
    with pytest.raises(PlatformPublisherAdapterError, match="does not match"):
        YouTubePublisher(
            authorization_reference="oauth-ref-account-001",
            transport=_Transport(),
        ).publish(_package("tiktok"))
