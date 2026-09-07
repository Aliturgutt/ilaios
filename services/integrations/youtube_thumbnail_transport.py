"""Additive YouTube thumbnail upload wrapper for governed publication.

This module wraps the existing YouTube publication transport. It never selects an
account, owns retries, or creates a second publication authority. Thumbnail upload
runs only after the existing video upload succeeds and is bound to explicit
package metadata plus SHA-256 evidence.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from services.integrations.social_publishing import SocialPublishTransportResult
from services.integrations.social_publishing_transports import (
    OAuthCredentialResolver,
    SocialHttpClient,
    SocialPublicationAmbiguousError,
    SocialPublicationTransportError,
    UrllibSocialHttpClient,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class YouTubeThumbnailUploadTransport:
    provider_name = "youtube-data-api-v3"
    required_scope = "https://www.googleapis.com/auth/youtube.upload"

    def __init__(
        self,
        *,
        inner: object,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        require_thumbnail: bool = True,
    ) -> None:
        if not hasattr(inner, "publish"):
            raise SocialPublicationTransportError("inner transport must implement publish")
        self._inner = inner
        self._resolver = credential_resolver
        self._http = http or UrllibSocialHttpClient()
        self._require_thumbnail = require_thumbnail

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult:
        result = self._inner.publish(
            platform=platform,
            account_id=account_id,
            oauth_authorization_ref=oauth_authorization_ref,
            package=package,
        )
        if not result.succeeded:
            return result
        if platform != "youtube":
            raise SocialPublicationTransportError("thumbnail wrapper requires youtube platform")
        if result.platform_post_id is None:
            raise SocialPublicationAmbiguousError("successful YouTube publication omitted video id")

        thumbnail_path = package.metadata.get("youtube_thumbnail_path")
        thumbnail_sha = package.metadata.get("youtube_thumbnail_sha256")
        if not thumbnail_path and not thumbnail_sha:
            if self._require_thumbnail:
                raise SocialPublicationAmbiguousError(
                    "YouTube video published but required thumbnail evidence is missing"
                )
            return result
        if not thumbnail_path or not thumbnail_sha:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail path/SHA metadata is incomplete"
            )

        data = Path(thumbnail_path).read_bytes()
        actual_sha = sha256(data).hexdigest()
        if actual_sha != thumbnail_sha:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail SHA-256 does not match package evidence"
            )

        credential = self._resolver.resolve(oauth_authorization_ref)
        if credential.authorization_ref != oauth_authorization_ref:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail credential reference mismatched"
            )
        if credential.account_id != account_id:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail credential account mismatched"
            )
        if self.required_scope not in credential.scopes:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail credential lacks youtube.upload scope"
            )

        suffix = Path(thumbnail_path).suffix.lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }.get(suffix)
        if content_type is None:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail format is not JPEG/PNG"
            )

        query = urlencode({"videoId": result.platform_post_id, "uploadType": "media"})
        try:
            response = self._http.request(
                method="POST",
                url=f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?{query}",
                headers={
                    "Authorization": f"Bearer {credential.access_token}",
                    "Content-Type": content_type,
                    "Content-Length": str(len(data)),
                },
                body=data,
            )
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but thumbnail upload outcome is unknown"
            ) from exc
        if response.status_code != 200:
            raise SocialPublicationAmbiguousError(
                f"YouTube video published but thumbnail upload returned HTTP {response.status_code}"
            )
        return result
