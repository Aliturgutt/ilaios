"""Concrete one-attempt social publication transports for Video Factory.

These transports sit behind the existing OAuth-reference-bound adapters and the
DurablePublishingCoordinator. They never select accounts, retry a publish POST,
or own idempotency. Credentials are resolved server-side from an opaque OAuth
reference. A network/response ambiguity after a side-effectful request is raised
so the coordinator records AMBIGUOUS and prohibits blind reposting.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from services.integrations.social_publishing import (
    SocialPublishTransportResult,
)
from src.video_automation.publishing_package_preparation import PlatformPublishingPackage


class SocialPublicationTransportError(ValueError):
    """Raised for deterministic precondition or explicit platform failures."""


class SocialPublicationAmbiguousError(RuntimeError):
    """Raised when a remote side effect may have happened but cannot be proven."""


@dataclass(frozen=True, slots=True)
class ResolvedOAuthCredential:
    authorization_ref: str
    account_id: str
    access_token: str
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("authorization_ref", self.authorization_ref),
            ("account_id", self.account_id),
            ("access_token", self.access_token),
        ):
            _text(name, value)
        if not self.scopes or len(self.scopes) != len(set(self.scopes)):
            raise SocialPublicationTransportError(
                "resolved OAuth credential scopes must be non-empty and unique"
            )
        for scope in self.scopes:
            _text("OAuth scope", scope)


class OAuthCredentialResolver(Protocol):
    def resolve(self, authorization_ref: str) -> ResolvedOAuthCredential: ...


@dataclass(frozen=True, slots=True)
class SocialHttpResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status_code < 100 or self.status_code > 599:
            raise SocialPublicationTransportError("invalid HTTP status code")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


class SocialHttpClient(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout_seconds: int = 60,
    ) -> SocialHttpResponse: ...


class UrllibSocialHttpClient:
    """Small synchronous HTTP client; HTTP errors are explicit responses."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout_seconds: int = 60,
    ) -> SocialHttpResponse:
        request = urllib.request.Request(
            url,
            data=body,
            headers=dict(headers),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return SocialHttpResponse(
                    status_code=int(response.status),
                    body=response.read(),
                    headers=dict(response.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            return SocialHttpResponse(
                status_code=int(exc.code),
                body=exc.read(),
                headers=dict(exc.headers.items()) if exc.headers is not None else {},
            )


class _OAuthTransportBase:
    def __init__(
        self,
        *,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._resolver = credential_resolver
        self._http = http or UrllibSocialHttpClient()
        self._sleep = sleep

    def _credential(
        self,
        *,
        authorization_ref: str,
        account_id: str,
        required_scope: str,
    ) -> ResolvedOAuthCredential:
        credential = self._resolver.resolve(authorization_ref)
        if credential.authorization_ref != authorization_ref:
            raise SocialPublicationTransportError(
                "resolved credential authorization reference mismatch"
            )
        if credential.account_id != account_id:
            raise SocialPublicationTransportError(
                "resolved credential account does not match publishing target"
            )
        if required_scope not in credential.scopes:
            raise SocialPublicationTransportError(
                f"resolved credential is missing required scope: {required_scope}"
            )
        return credential


class YouTubeSocialPublishTransport(_OAuthTransportBase):
    """Upload one MP4 and wait for YouTube processing to succeed."""

    provider_name = "youtube-data-api-v3"
    required_scope = "https://www.googleapis.com/auth/youtube.upload"

    def __init__(
        self,
        *,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        sleep: Callable[[float], None] = time.sleep,
        processing_attempts: int = 60,
        processing_interval_seconds: float = 2.0,
    ) -> None:
        super().__init__(
            credential_resolver=credential_resolver,
            http=http,
            sleep=sleep,
        )
        if processing_attempts <= 0 or processing_interval_seconds < 0:
            raise SocialPublicationTransportError(
                "YouTube processing bounds must be positive/non-negative"
            )
        self._processing_attempts = processing_attempts
        self._processing_interval_seconds = processing_interval_seconds

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult:
        if platform != "youtube":
            return _failure(self.provider_name, "platform_mismatch", "expected youtube")
        try:
            credential = self._credential(
                authorization_ref=oauth_authorization_ref,
                account_id=account_id,
                required_scope=self.required_scope,
            )
            media = _verified_media(package)
            privacy = _youtube_privacy(package.visibility)
        except SocialPublicationTransportError as exc:
            return _failure(self.provider_name, "precondition_failed", str(exc))

        boundary = f"ilaios-{package.package_id}"
        metadata = json.dumps(
            {
                "snippet": {
                    "title": package.title,
                    "description": package.description,
                    "tags": list(package.tags),
                },
                "status": {"privacyStatus": privacy},
            },
            separators=(",", ":"),
        ).encode("utf-8")
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
            + metadata
            + f"\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n".encode()
            + media
            + f"\r\n--{boundary}--\r\n".encode()
        )
        url = (
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=multipart&part=snippet,status"
        )
        response = self._side_effect_request(
            method="POST",
            url=url,
            headers={
                "Authorization": f"Bearer {credential.access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            body=body,
        )
        if response.status_code not in {200, 201}:
            return _http_failure(self.provider_name, "youtube_upload_failed", response)
        payload = _json_object(response)
        video_id = payload.get("id")
        if not isinstance(video_id, str) or not video_id.strip():
            raise SocialPublicationAmbiguousError(
                "YouTube upload returned success without a video ID"
            )

        for _ in range(self._processing_attempts):
            query = urllib.parse.urlencode(
                {
                    "part": "processingDetails,status",
                    "id": video_id,
                }
            )
            verify = self._safe_read_request(
                method="GET",
                url=f"https://www.googleapis.com/youtube/v3/videos?{query}",
                headers={"Authorization": f"Bearer {credential.access_token}"},
            )
            if verify.status_code != 200:
                raise SocialPublicationAmbiguousError(
                    f"YouTube processing verification returned HTTP {verify.status_code}"
                )
            verify_payload = _json_object(verify)
            items = verify_payload.get("items")
            if not isinstance(items, list) or not items or not isinstance(items[0], dict):
                raise SocialPublicationAmbiguousError(
                    "YouTube processing verification omitted uploaded video"
                )
            details = items[0].get("processingDetails")
            if not isinstance(details, dict):
                raise SocialPublicationAmbiguousError(
                    "YouTube processingDetails are missing"
                )
            status = details.get("processingStatus")
            if status == "succeeded":
                return SocialPublishTransportResult(
                    succeeded=True,
                    provider_name=self.provider_name,
                    platform_post_id=video_id,
                    published_url=f"https://www.youtube.com/watch?v={video_id}",
                )
            if status in {"failed", "terminated"}:
                return _failure(
                    self.provider_name,
                    "youtube_processing_failed",
                    f"YouTube processing ended with status {status}",
                )
            self._sleep(self._processing_interval_seconds)
        raise SocialPublicationAmbiguousError(
            "YouTube processing did not reach a terminal state inside the bounded window"
        )

    def _side_effect_request(self, **kwargs: object) -> SocialHttpResponse:
        try:
            return self._http.request(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "YouTube upload request outcome is unknown"
            ) from exc

    def _safe_read_request(self, **kwargs: object) -> SocialHttpResponse:
        try:
            return self._http.request(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "YouTube verification request failed after upload"
            ) from exc


class TikTokSocialPublishTransport(_OAuthTransportBase):
    """Direct-post one MP4 after latest creator-info and explicit-consent checks."""

    provider_name = "tiktok-content-posting-api-v2"
    required_scope = "video.publish"
    _max_single_upload_bytes = 64 * 1024 * 1024

    def __init__(
        self,
        *,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        sleep: Callable[[float], None] = time.sleep,
        status_attempts: int = 90,
        status_interval_seconds: float = 2.0,
    ) -> None:
        super().__init__(
            credential_resolver=credential_resolver,
            http=http,
            sleep=sleep,
        )
        if status_attempts <= 0 or status_interval_seconds < 0:
            raise SocialPublicationTransportError(
                "TikTok status bounds must be positive/non-negative"
            )
        self._status_attempts = status_attempts
        self._status_interval_seconds = status_interval_seconds

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult:
        if platform != "tiktok":
            return _failure(self.provider_name, "platform_mismatch", "expected tiktok")
        try:
            credential = self._credential(
                authorization_ref=oauth_authorization_ref,
                account_id=account_id,
                required_scope=self.required_scope,
            )
            media = _verified_media(package)
            if len(media) > self._max_single_upload_bytes:
                raise SocialPublicationTransportError(
                    "TikTok governed FILE_UPLOAD currently requires media <= 64 MiB"
                )
            consent_ref = _required_metadata(package, "tiktok_upload_consent_ref")
            privacy = _required_metadata(package, "tiktok_privacy_level")
            duration = int(_required_metadata(package, "video_duration_seconds"))
            disable_comment = _metadata_bool(package, "tiktok_disable_comment")
            disable_duet = _metadata_bool(package, "tiktok_disable_duet")
            disable_stitch = _metadata_bool(package, "tiktok_disable_stitch")
            is_aigc = _metadata_bool(package, "tiktok_is_aigc")
            _text("tiktok_upload_consent_ref", consent_ref)
            if duration <= 0:
                raise SocialPublicationTransportError(
                    "video_duration_seconds must be positive"
                )
        except (SocialPublicationTransportError, ValueError) as exc:
            return _failure(self.provider_name, "precondition_failed", str(exc))

        headers = {
            "Authorization": f"Bearer {credential.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        creator_response = self._read_json_post(
            "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
            headers,
            {},
            after_side_effect=False,
        )
        creator_error = _tiktok_error(creator_response)
        if creator_error is not None:
            return _failure(self.provider_name, creator_error[0], creator_error[1])
        creator = _json_object(creator_response).get("data")
        if not isinstance(creator, dict):
            return _failure(
                self.provider_name,
                "tiktok_creator_info_invalid",
                "TikTok creator-info response omitted data",
            )
        options = creator.get("privacy_level_options")
        if not isinstance(options, list) or privacy not in options:
            return _failure(
                self.provider_name,
                "tiktok_privacy_not_allowed",
                "requested privacy is not allowed by latest creator info",
            )
        max_duration = creator.get("max_video_post_duration_sec")
        if not isinstance(max_duration, int) or duration > max_duration:
            return _failure(
                self.provider_name,
                "tiktok_duration_not_allowed",
                "video exceeds latest creator duration privilege",
            )
        for requested_disabled, creator_disabled, label in (
            (disable_comment, creator.get("comment_disabled"), "comment"),
            (disable_duet, creator.get("duet_disabled"), "duet"),
            (disable_stitch, creator.get("stitch_disabled"), "stitch"),
        ):
            if creator_disabled is True and requested_disabled is False:
                return _failure(
                    self.provider_name,
                    "tiktok_interaction_not_allowed",
                    f"latest creator settings require {label} to be disabled",
                )

        init_payload = {
            "post_info": {
                "title": package.description,
                "privacy_level": privacy,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": len(media),
                "chunk_size": len(media),
                "total_chunk_count": 1,
            },
            "is_aigc": is_aigc,
        }
        init = self._read_json_post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers,
            init_payload,
            after_side_effect=True,
        )
        init_error = _tiktok_error(init)
        if init_error is not None:
            return _failure(self.provider_name, init_error[0], init_error[1])
        init_data = _json_object(init).get("data")
        if not isinstance(init_data, dict):
            raise SocialPublicationAmbiguousError(
                "TikTok init succeeded without publication data"
            )
        publish_id = init_data.get("publish_id")
        upload_url = init_data.get("upload_url")
        if not isinstance(publish_id, str) or not isinstance(upload_url, str):
            raise SocialPublicationAmbiguousError(
                "TikTok init succeeded without publish_id/upload_url"
            )

        upload = self._side_effect_request(
            method="PUT",
            url=upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(media)),
                "Content-Range": f"bytes 0-{len(media) - 1}/{len(media)}",
            },
            body=media,
            timeout_seconds=120,
        )
        if upload.status_code not in {200, 201, 202, 204}:
            return _http_failure(self.provider_name, "tiktok_upload_failed", upload)

        creator_username = creator.get("creator_username")
        for _ in range(self._status_attempts):
            status_response = self._read_json_post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers,
                {"publish_id": publish_id},
                after_side_effect=True,
            )
            status_error = _tiktok_error(status_response)
            if status_error is not None:
                raise SocialPublicationAmbiguousError(
                    f"TikTok status fetch failed: {status_error[0]}"
                )
            data = _json_object(status_response).get("data")
            if not isinstance(data, dict):
                raise SocialPublicationAmbiguousError(
                    "TikTok status response omitted data"
                )
            status = data.get("status")
            if status == "FAILED":
                return _failure(
                    self.provider_name,
                    "tiktok_publish_failed",
                    str(data.get("fail_reason") or "TikTok publication failed"),
                )
            if status == "PUBLISH_COMPLETE":
                ids = data.get("publicaly_available_post_id")
                if not isinstance(ids, list) or not ids:
                    return _failure(
                        self.provider_name,
                        "tiktok_public_post_id_unavailable",
                        "TikTok completed the post but did not expose a public post ID",
                    )
                post_id = str(ids[0])
                published_url = (
                    f"https://www.tiktok.com/@{creator_username}/video/{post_id}"
                    if isinstance(creator_username, str) and creator_username
                    else None
                )
                return SocialPublishTransportResult(
                    succeeded=True,
                    provider_name=self.provider_name,
                    platform_post_id=post_id,
                    published_url=published_url,
                )
            self._sleep(self._status_interval_seconds)
        raise SocialPublicationAmbiguousError(
            "TikTok post did not reach a terminal state inside the bounded window"
        )

    def _read_json_post(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        *,
        after_side_effect: bool,
    ) -> SocialHttpResponse:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        try:
            return self._http.request(
                method="POST",
                url=url,
                headers=headers,
                body=body,
                timeout_seconds=60,
            )
        except Exception as exc:
            if after_side_effect:
                raise SocialPublicationAmbiguousError(
                    "TikTok request failed after publication side effects began"
                ) from exc
            raise SocialPublicationTransportError(
                "TikTok creator-info request failed before publication"
            ) from exc

    def _side_effect_request(self, **kwargs: object) -> SocialHttpResponse:
        try:
            return self._http.request(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "TikTok upload outcome is unknown"
            ) from exc


class InstagramSocialPublishTransport(_OAuthTransportBase):
    """Publish one Reel from an explicitly hash-bound public media URL."""

    provider_name = "instagram-graph-api"
    required_scope = "instagram_content_publish"

    def __init__(
        self,
        *,
        credential_resolver: OAuthCredentialResolver,
        http: SocialHttpClient | None = None,
        sleep: Callable[[float], None] = time.sleep,
        api_version: str = "v23.0",
        container_attempts: int = 60,
        container_interval_seconds: float = 2.0,
    ) -> None:
        super().__init__(
            credential_resolver=credential_resolver,
            http=http,
            sleep=sleep,
        )
        _text("api_version", api_version)
        if container_attempts <= 0 or container_interval_seconds < 0:
            raise SocialPublicationTransportError(
                "Instagram container bounds must be positive/non-negative"
            )
        self._api_version = api_version
        self._container_attempts = container_attempts
        self._container_interval_seconds = container_interval_seconds

    def publish(
        self,
        *,
        platform: str,
        account_id: str,
        oauth_authorization_ref: str,
        package: PlatformPublishingPackage,
    ) -> SocialPublishTransportResult:
        if platform != "instagram":
            return _failure(self.provider_name, "platform_mismatch", "expected instagram")
        try:
            credential = self._credential(
                authorization_ref=oauth_authorization_ref,
                account_id=account_id,
                required_scope=self.required_scope,
            )
            _verified_media(package)
            public_url = _required_metadata(package, "instagram_video_url")
            public_sha = _required_metadata(package, "instagram_video_sha256")
            if public_sha != package.media_sha256_hex:
                raise SocialPublicationTransportError(
                    "Instagram public media URL is not declared as the exact final MP4 SHA"
                )
            parsed = urllib.parse.urlparse(public_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise SocialPublicationTransportError(
                    "instagram_video_url must be a public HTTPS URL"
                )
            share_to_feed = _metadata_bool(
                package,
                "instagram_share_to_feed",
                default=False,
            )
        except SocialPublicationTransportError as exc:
            return _failure(self.provider_name, "precondition_failed", str(exc))

        auth = {"Authorization": f"Bearer {credential.access_token}"}
        create_body = urllib.parse.urlencode(
            {
                "media_type": "REELS",
                "video_url": public_url,
                "caption": package.description,
                "share_to_feed": "true" if share_to_feed else "false",
            }
        ).encode("utf-8")
        create = self._side_effect_request(
            method="POST",
            url=f"https://graph.instagram.com/{self._api_version}/{account_id}/media",
            headers={**auth, "Content-Type": "application/x-www-form-urlencoded"},
            body=create_body,
            timeout_seconds=60,
        )
        if create.status_code not in {200, 201}:
            return _http_failure(self.provider_name, "instagram_container_failed", create)
        container_id = _json_object(create).get("id")
        if not isinstance(container_id, str) or not container_id:
            raise SocialPublicationAmbiguousError(
                "Instagram container creation succeeded without container ID"
            )

        for _ in range(self._container_attempts):
            status_query = urllib.parse.urlencode({"fields": "status_code,status"})
            try:
                status_response = self._http.request(
                    method="GET",
                    url=(
                        f"https://graph.instagram.com/{self._api_version}/{container_id}"
                        f"?{status_query}"
                    ),
                    headers=auth,
                    timeout_seconds=60,
                )
            except Exception as exc:
                raise SocialPublicationAmbiguousError(
                    "Instagram container status is unknown"
                ) from exc
            if status_response.status_code != 200:
                raise SocialPublicationAmbiguousError(
                    "Instagram container status lookup failed after container creation"
                )
            status_payload = _json_object(status_response)
            status = status_payload.get("status_code")
            if status == "FINISHED":
                break
            if status in {"ERROR", "EXPIRED"}:
                return _failure(
                    self.provider_name,
                    "instagram_container_processing_failed",
                    str(status_payload.get("status") or status),
                )
            self._sleep(self._container_interval_seconds)
        else:
            raise SocialPublicationAmbiguousError(
                "Instagram container did not become publishable inside the bounded window"
            )

        publish_body = urllib.parse.urlencode({"creation_id": container_id}).encode("utf-8")
        publish = self._side_effect_request(
            method="POST",
            url=(
                f"https://graph.instagram.com/{self._api_version}/{account_id}/media_publish"
            ),
            headers={**auth, "Content-Type": "application/x-www-form-urlencoded"},
            body=publish_body,
            timeout_seconds=60,
        )
        if publish.status_code not in {200, 201}:
            return _http_failure(self.provider_name, "instagram_publish_failed", publish)
        media_id = _json_object(publish).get("id")
        if not isinstance(media_id, str) or not media_id:
            raise SocialPublicationAmbiguousError(
                "Instagram publish succeeded without media ID"
            )

        permalink_query = urllib.parse.urlencode({"fields": "permalink"})
        try:
            permalink_response = self._http.request(
                method="GET",
                url=(
                    f"https://graph.instagram.com/{self._api_version}/{media_id}"
                    f"?{permalink_query}"
                ),
                headers=auth,
                timeout_seconds=60,
            )
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "Instagram post exists but permalink verification failed"
            ) from exc
        if permalink_response.status_code != 200:
            raise SocialPublicationAmbiguousError(
                "Instagram post exists but permalink verification was not successful"
            )
        permalink = _json_object(permalink_response).get("permalink")
        if not isinstance(permalink, str) or not permalink:
            raise SocialPublicationAmbiguousError(
                "Instagram post exists but permalink was not returned"
            )
        return SocialPublishTransportResult(
            succeeded=True,
            provider_name=self.provider_name,
            platform_post_id=media_id,
            published_url=permalink,
        )

    def _side_effect_request(self, **kwargs: object) -> SocialHttpResponse:
        try:
            return self._http.request(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise SocialPublicationAmbiguousError(
                "Instagram publication request outcome is unknown"
            ) from exc


def _verified_media(package: PlatformPublishingPackage) -> bytes:
    media_path = Path(package.media_path)
    if media_path.is_symlink() or not media_path.is_file():
        raise SocialPublicationTransportError(
            "publishing media must be an existing regular file"
        )
    media = media_path.read_bytes()
    if len(media) != package.media_byte_length:
        raise SocialPublicationTransportError("publishing media byte length mismatch")
    if sha256(media).hexdigest() != package.media_sha256_hex:
        raise SocialPublicationTransportError("publishing media SHA-256 mismatch")
    return media


def _youtube_privacy(visibility: str) -> str:
    normalized = visibility.strip().lower()
    mapping = {
        "private": "private",
        "public": "public",
        "unlisted": "unlisted",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise SocialPublicationTransportError(
            "YouTube visibility must be private, public, or unlisted"
        ) from exc


def _required_metadata(package: PlatformPublishingPackage, key: str) -> str:
    value = package.metadata.get(key)
    if value is None:
        raise SocialPublicationTransportError(f"required publishing metadata missing: {key}")
    _text(key, value)
    return value


def _metadata_bool(
    package: PlatformPublishingPackage,
    key: str,
    *,
    default: bool | None = None,
) -> bool:
    value = package.metadata.get(key)
    if value is None:
        if default is not None:
            return default
        raise SocialPublicationTransportError(f"required publishing metadata missing: {key}")
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise SocialPublicationTransportError(f"{key} must be true or false")


def _json_object(response: SocialHttpResponse) -> dict[str, object]:
    try:
        parsed = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SocialPublicationAmbiguousError("platform returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise SocialPublicationAmbiguousError("platform returned non-object JSON")
    return parsed


def _tiktok_error(response: SocialHttpResponse) -> tuple[str, str] | None:
    if response.status_code < 200 or response.status_code >= 300:
        return (
            f"tiktok_http_{response.status_code}",
            _response_excerpt(response),
        )
    payload = _json_object(response)
    error = payload.get("error")
    if not isinstance(error, dict):
        return ("tiktok_error_missing", "TikTok response omitted error envelope")
    code = error.get("code")
    if code == "ok":
        return None
    return (
        str(code or "tiktok_unknown_error"),
        str(error.get("message") or "TikTok request failed"),
    )


def _http_failure(
    provider_name: str,
    code: str,
    response: SocialHttpResponse,
) -> SocialPublishTransportResult:
    return _failure(
        provider_name,
        code,
        f"HTTP {response.status_code}: {_response_excerpt(response)}",
    )


def _failure(
    provider_name: str,
    code: str,
    message: str,
) -> SocialPublishTransportResult:
    return SocialPublishTransportResult(
        succeeded=False,
        provider_name=provider_name,
        error_code=code,
        error_message=message,
    )


def _response_excerpt(response: SocialHttpResponse) -> str:
    return response.body.decode("utf-8", errors="replace")[:500] or "empty response"


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise SocialPublicationTransportError(
            f"{name} must be normalized non-blank text"
        )
