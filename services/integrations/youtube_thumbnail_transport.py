"""Additive YouTube metadata/thumbnail wrapper for governed publication.

This module wraps the existing YouTube publication transport. It never selects an
account, owns retries, or creates a second publication authority. Platform metadata
and thumbnail side effects run only after the existing video upload succeeds and
remain bound to the same OAuth reference and package evidence.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from services.integrations.social_publishing import (
    SocialPublishTransport,
    SocialPublishTransportResult,
)
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
    _metadata_keys = (
        "youtube_category_id",
        "youtube_default_language",
        "youtube_self_declared_made_for_kids",
        "youtube_contains_synthetic_media",
    )

    def __init__(
        self,
        *,
        inner: SocialPublishTransport,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        require_thumbnail: bool = True,
    ) -> None:
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
        if platform != "youtube":
            raise SocialPublicationTransportError("YouTube wrapper requires youtube platform")
        metadata_payload = self._planned_metadata_payload(package)

        result = self._inner.publish(
            platform=platform,
            account_id=account_id,
            oauth_authorization_ref=oauth_authorization_ref,
            package=package,
        )
        if not result.succeeded:
            return result
        if result.platform_post_id is None:
            raise SocialPublicationAmbiguousError("successful YouTube publication omitted video id")

        credential = self._resolver.resolve(oauth_authorization_ref)
        if credential.authorization_ref != oauth_authorization_ref:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but credential reference mismatched"
            )
        if credential.account_id != account_id:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but credential account mismatched"
            )
        if self.required_scope not in credential.scopes:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but credential lacks youtube.upload scope"
            )

        if metadata_payload is not None:
            self._apply_metadata(
                video_id=result.platform_post_id,
                access_token=credential.access_token,
                payload=metadata_payload,
            )

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

    def _planned_metadata_payload(
        self,
        package: PlatformPublishingPackage,
    ) -> dict[str, object] | None:
        present = [key for key in self._metadata_keys if key in package.metadata]
        if not present:
            return None
        if len(present) != len(self._metadata_keys):
            raise SocialPublicationTransportError(
                "planned YouTube platform metadata is incomplete"
            )
        category_id = package.metadata["youtube_category_id"].strip()
        language = package.metadata["youtube_default_language"].strip()
        if not category_id.isdigit():
            raise SocialPublicationTransportError(
                "youtube_category_id must be numeric"
            )
        if not language:
            raise SocialPublicationTransportError(
                "youtube_default_language must be non-blank"
            )
        return {
            "id": "__VIDEO_ID__",
            "snippet": {
                "title": package.title,
                "description": package.description,
                "tags": list(package.tags),
                "categoryId": category_id,
                "defaultLanguage": language,
            },
            "status": {
                "privacyStatus": package.visibility,
                "selfDeclaredMadeForKids": self._metadata_bool(
                    package,
                    "youtube_self_declared_made_for_kids",
                ),
                "containsSyntheticMedia": self._metadata_bool(
                    package,
                    "youtube_contains_synthetic_media",
                ),
            },
        }

    @staticmethod
    def _metadata_bool(package: PlatformPublishingPackage, key: str) -> bool:
        value = package.metadata[key].strip().lower()
        if value == "true":
            return True
        if value == "false":
            return False
        raise SocialPublicationTransportError(f"{key} must be true or false")

    def _apply_metadata(
        self,
        *,
        video_id: str,
        access_token: str,
        payload: dict[str, object],
    ) -> None:
        payload = dict(payload)
        payload["id"] = video_id
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        query = urlencode({"part": "snippet,status"})
        try:
            response = self._http.request(
                method="PUT",
                url=f"https://www.googleapis.com/youtube/v3/videos?{query}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "Content-Length": str(len(body)),
                },
                body=body,
            )
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but platform metadata update outcome is unknown"
            ) from exc
        if response.status_code != 200:
            raise SocialPublicationAmbiguousError(
                "YouTube video published but platform metadata update failed with "
                f"HTTP {response.status_code}"
            )
