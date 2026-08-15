from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from services.integrations.social_publishing_transports import (
    InstagramSocialPublishTransport,
    ResolvedOAuthCredential,
    SocialHttpResponse,
    SocialPublicationAmbiguousError,
    TikTokSocialPublishTransport,
    YouTubeSocialPublishTransport,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class _Resolver:
    def __init__(self, credential: ResolvedOAuthCredential) -> None:
        self.credential = credential
        self.calls = 0

    def resolve(self, authorization_ref: str) -> ResolvedOAuthCredential:
        self.calls += 1
        assert authorization_ref == self.credential.authorization_ref
        return self.credential


class _Http:
    def __init__(self, responses: list[SocialHttpResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | object,
        body: bytes | None = None,
        timeout_seconds: int = 60,
    ) -> SocialHttpResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "timeout_seconds": timeout_seconds,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _json(status: int, value: object) -> SocialHttpResponse:
    return SocialHttpResponse(
        status_code=status,
        body=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def _package(
    tmp_path: Path,
    *,
    platform: str,
    metadata: dict[str, str] | None = None,
    visibility: str = "private",
) -> PlatformPublishingPackage:
    media = tmp_path / f"{platform}.mp4"
    media.write_bytes(b"real-final-mp4-proof-bytes")
    body = media.read_bytes()
    return PlatformPublishingPackage(
        package_id=f"package-{platform}",
        episode_id="episode-001",
        artifact_id="artifact-001",
        acceptance_decision_id="acceptance-001",
        platform=platform,
        account_id=f"{platform}-account",
        media_path=str(media),
        media_sha256_hex=sha256(body).hexdigest(),
        media_byte_length=len(body),
        scheduled_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
        visibility=visibility,
        title="ILAIOS Video",
        description="ILAIOS production publication proof",
        tags=("ilaios", "ai"),
        metadata=metadata or {},
    )


def _credential(
    *,
    platform: str,
    scope: str,
) -> ResolvedOAuthCredential:
    return ResolvedOAuthCredential(
        authorization_ref=f"oauth://{platform}/test",
        account_id=f"{platform}-account",
        access_token="server-side-token",
        scopes=(scope,),
    )


def test_youtube_upload_waits_for_processing_success(tmp_path: Path) -> None:
    package = _package(tmp_path, platform="youtube", visibility="unlisted")
    resolver = _Resolver(
        _credential(
            platform="youtube",
            scope="https://www.googleapis.com/auth/youtube.upload",
        )
    )
    http = _Http(
        [
            _json(200, {"id": "youtube-video-001"}),
            _json(
                200,
                {
                    "items": [
                        {"processingDetails": {"processingStatus": "processing"}}
                    ]
                },
            ),
            _json(
                200,
                {
                    "items": [
                        {"processingDetails": {"processingStatus": "succeeded"}}
                    ]
                },
            ),
        ]
    )
    transport = YouTubeSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
        sleep=lambda _: None,
        processing_attempts=3,
    )

    result = transport.publish(
        platform="youtube",
        account_id=package.account_id,
        oauth_authorization_ref="oauth://youtube/test",
        package=package,
    )

    assert result.succeeded is True
    assert result.platform_post_id == "youtube-video-001"
    assert result.published_url == "https://www.youtube.com/watch?v=youtube-video-001"
    assert len(http.calls) == 3
    upload_body = http.calls[0]["body"]
    assert isinstance(upload_body, bytes)
    assert b'"privacyStatus":"unlisted"' in upload_body
    assert b"real-final-mp4-proof-bytes" in upload_body


def test_youtube_unknown_upload_outcome_raises_ambiguous(tmp_path: Path) -> None:
    package = _package(tmp_path, platform="youtube")
    resolver = _Resolver(
        _credential(
            platform="youtube",
            scope="https://www.googleapis.com/auth/youtube.upload",
        )
    )
    http = _Http([TimeoutError("connection dropped after upload")])
    transport = YouTubeSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
    )

    with pytest.raises(SocialPublicationAmbiguousError, match="outcome is unknown"):
        transport.publish(
            platform="youtube",
            account_id=package.account_id,
            oauth_authorization_ref="oauth://youtube/test",
            package=package,
        )


def test_tiktok_requires_explicit_consent_and_latest_creator_privileges(
    tmp_path: Path,
) -> None:
    package = _package(
        tmp_path,
        platform="tiktok",
        metadata={
            "tiktok_upload_consent_ref": "consent://tiktok/upload/001",
            "tiktok_privacy_level": "PUBLIC_TO_EVERYONE",
            "video_duration_seconds": "4",
            "tiktok_disable_comment": "false",
            "tiktok_disable_duet": "false",
            "tiktok_disable_stitch": "false",
            "tiktok_is_aigc": "true",
        },
        visibility="public",
    )
    resolver = _Resolver(_credential(platform="tiktok", scope="video.publish"))
    http = _Http(
        [
            _json(
                200,
                {
                    "data": {
                        "creator_username": "ilaios_test",
                        "privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"],
                        "comment_disabled": False,
                        "duet_disabled": False,
                        "stitch_disabled": False,
                        "max_video_post_duration_sec": 60,
                    },
                    "error": {"code": "ok", "message": ""},
                },
            ),
            _json(
                200,
                {
                    "data": {
                        "publish_id": "publish-001",
                        "upload_url": "https://upload.tiktok.example/001",
                    },
                    "error": {"code": "ok", "message": ""},
                },
            ),
            SocialHttpResponse(status_code=200, body=b"", headers={}),
            _json(
                200,
                {
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": [987654321],
                        "uploaded_bytes": package.media_byte_length,
                    },
                    "error": {"code": "ok", "message": ""},
                },
            ),
        ]
    )
    transport = TikTokSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
        sleep=lambda _: None,
    )

    result = transport.publish(
        platform="tiktok",
        account_id=package.account_id,
        oauth_authorization_ref="oauth://tiktok/test",
        package=package,
    )

    assert result.succeeded is True
    assert result.platform_post_id == "987654321"
    assert result.published_url == "https://www.tiktok.com/@ilaios_test/video/987654321"
    assert [call["method"] for call in http.calls] == ["POST", "POST", "PUT", "POST"]
    init_body = http.calls[1]["body"]
    assert isinstance(init_body, bytes)
    assert b'"is_aigc":true' in init_body
    assert b'"privacy_level":"PUBLIC_TO_EVERYONE"' in init_body


def test_tiktok_missing_consent_fails_before_http(tmp_path: Path) -> None:
    package = _package(
        tmp_path,
        platform="tiktok",
        metadata={
            "tiktok_privacy_level": "SELF_ONLY",
            "video_duration_seconds": "4",
            "tiktok_disable_comment": "true",
            "tiktok_disable_duet": "true",
            "tiktok_disable_stitch": "true",
            "tiktok_is_aigc": "true",
        },
    )
    resolver = _Resolver(_credential(platform="tiktok", scope="video.publish"))
    http = _Http([])
    transport = TikTokSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
    )

    result = transport.publish(
        platform="tiktok",
        account_id=package.account_id,
        oauth_authorization_ref="oauth://tiktok/test",
        package=package,
    )

    assert result.succeeded is False
    assert result.error_code == "precondition_failed"
    assert http.calls == []


def test_instagram_reel_requires_hash_bound_https_source_and_permalink(
    tmp_path: Path,
) -> None:
    base = _package(tmp_path, platform="instagram")
    package = _package(
        tmp_path,
        platform="instagram",
        metadata={
            "instagram_video_url": "https://cdn.example.test/final.mp4",
            "instagram_video_sha256": base.media_sha256_hex,
            "instagram_share_to_feed": "false",
        },
    )
    resolver = _Resolver(
        _credential(platform="instagram", scope="instagram_content_publish")
    )
    http = _Http(
        [
            _json(200, {"id": "container-001"}),
            _json(200, {"status_code": "IN_PROGRESS", "status": "Processing"}),
            _json(200, {"status_code": "FINISHED", "status": "Finished"}),
            _json(200, {"id": "instagram-media-001"}),
            _json(200, {"permalink": "https://www.instagram.com/reel/ABC123/"}),
        ]
    )
    transport = InstagramSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
        sleep=lambda _: None,
        container_attempts=3,
    )

    result = transport.publish(
        platform="instagram",
        account_id=package.account_id,
        oauth_authorization_ref="oauth://instagram/test",
        package=package,
    )

    assert result.succeeded is True
    assert result.platform_post_id == "instagram-media-001"
    assert result.published_url == "https://www.instagram.com/reel/ABC123/"
    assert [call["method"] for call in http.calls] == ["POST", "GET", "GET", "POST", "GET"]


def test_instagram_wrong_hosted_sha_fails_before_side_effect(tmp_path: Path) -> None:
    package = _package(
        tmp_path,
        platform="instagram",
        metadata={
            "instagram_video_url": "https://cdn.example.test/final.mp4",
            "instagram_video_sha256": "0" * 64,
            "instagram_share_to_feed": "false",
        },
    )
    resolver = _Resolver(
        _credential(platform="instagram", scope="instagram_content_publish")
    )
    http = _Http([])
    transport = InstagramSocialPublishTransport(
        credential_resolver=resolver,
        http=http,
    )

    result = transport.publish(
        platform="instagram",
        account_id=package.account_id,
        oauth_authorization_ref="oauth://instagram/test",
        package=package,
    )

    assert result.succeeded is False
    assert result.error_code == "precondition_failed"
    assert http.calls == []
