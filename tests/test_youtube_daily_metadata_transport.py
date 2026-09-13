from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from services.integrations.social_publishing import SocialPublishTransportResult
from services.integrations.social_publishing_transports import (
    ResolvedOAuthCredential,
    SocialHttpResponse,
    SocialPublicationTransportError,
)
from services.integrations.youtube_thumbnail_transport import (
    YouTubeThumbnailUploadTransport,
)
from src.video_automation.publishing_package_preparation import (
    PlatformPublishingPackage,
)


class _Inner:
    def publish(self, **_: object) -> SocialPublishTransportResult:
        return SocialPublishTransportResult(
            succeeded=True,
            provider_name="youtube-data-api-v3",
            platform_post_id="video-001",
            published_url="https://www.youtube.com/watch?v=video-001",
        )


class _Resolver:
    def resolve(self, authorization_ref: str) -> ResolvedOAuthCredential:
        assert authorization_ref == "oauth://youtube/test"
        return ResolvedOAuthCredential(
            authorization_ref=authorization_ref,
            account_id="youtube-account",
            access_token="server-side-token",
            scopes=("https://www.googleapis.com/auth/youtube.upload",),
        )


class _Http:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def request(self, **kwargs: object) -> SocialHttpResponse:
        self.calls.append(dict(kwargs))
        return SocialHttpResponse(status_code=200, body=b"{}", headers={})


def _package(tmp_path: Path, *, metadata: dict[str, str]) -> PlatformPublishingPackage:
    media = tmp_path / "video.mp4"
    media.write_bytes(b"video-bytes")
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"thumbnail-bytes")
    metadata = dict(metadata)
    metadata.update(
        {
            "youtube_thumbnail_path": str(thumbnail),
            "youtube_thumbnail_sha256": sha256(thumbnail.read_bytes()).hexdigest(),
        }
    )
    return PlatformPublishingPackage(
        package_id="package-youtube",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform="youtube",
        account_id="youtube-account",
        media_path=str(media),
        media_sha256_hex=sha256(media.read_bytes()).hexdigest(),
        media_byte_length=len(media.read_bytes()),
        scheduled_at=datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc),
        visibility="private",
        title="AI infrastructure update",
        description="Evidence-bound daily episode.\n\n#AI #Technology #Business",
        tags=("ai", "technology", "business"),
        metadata=metadata,
    )


def test_daily_youtube_metadata_is_applied_before_thumbnail(tmp_path: Path) -> None:
    package = _package(
        tmp_path,
        metadata={
            "youtube_category_id": "28",
            "youtube_default_language": "en",
            "youtube_self_declared_made_for_kids": "false",
            "youtube_contains_synthetic_media": "true",
        },
    )
    http = _Http()
    transport = YouTubeThumbnailUploadTransport(
        inner=_Inner(),
        credential_resolver=_Resolver(),
        http=http,
    )

    result = transport.publish(
        platform="youtube",
        account_id="youtube-account",
        oauth_authorization_ref="oauth://youtube/test",
        package=package,
    )

    assert result.succeeded is True
    assert len(http.calls) == 2
    metadata_call = http.calls[0]
    assert metadata_call["method"] == "PUT"
    assert "youtube/v3/videos?part=snippet%2Cstatus" in str(metadata_call["url"])
    body = metadata_call["body"]
    assert isinstance(body, bytes)
    payload = json.loads(body.decode("utf-8"))
    assert payload["id"] == "video-001"
    assert payload["snippet"]["categoryId"] == "28"
    assert payload["snippet"]["defaultLanguage"] == "en"
    assert payload["status"]["selfDeclaredMadeForKids"] is False
    assert payload["status"]["containsSyntheticMedia"] is True
    assert http.calls[1]["method"] == "POST"
    assert "thumbnails/set" in str(http.calls[1]["url"])


def test_partial_daily_youtube_metadata_fails_before_upload(tmp_path: Path) -> None:
    package = _package(
        tmp_path,
        metadata={
            "youtube_category_id": "28",
            "youtube_default_language": "en",
        },
    )
    http = _Http()
    transport = YouTubeThumbnailUploadTransport(
        inner=_Inner(),
        credential_resolver=_Resolver(),
        http=http,
    )

    with pytest.raises(SocialPublicationTransportError, match="metadata is incomplete"):
        transport.publish(
            platform="youtube",
            account_id="youtube-account",
            oauth_authorization_ref="oauth://youtube/test",
            package=package,
        )

    assert http.calls == []
