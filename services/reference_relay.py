"""Short-lived signed HTTPS relay for provider-native private reference images.

The relay is deliberately separate from prompt text and from provider routing.
Private Desktop reference bytes are uploaded only after canonical admission and
are exposed to a provider through an unguessable, HMAC-signed, expiring HTTPS
URL. Tenant/principal identities remain server-side and are never embedded in
public URLs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, urlencode, urlparse

_MAX_RELAY_BYTES = 10 * 1024 * 1024
_DEFAULT_TTL_SECONDS = 1800
_MAX_TTL_SECONDS = 3600
_ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class ReferenceRelayError(RuntimeError):
    """Raised when a private reference cannot be safely relayed."""


@dataclass(frozen=True, slots=True)
class ReferenceRelayTicket:
    relay_id: str
    url: str
    sha256: str
    mime_type: str
    expires_at_epoch_s: int


class ReferenceRelay(Protocol):
    def publish(
        self,
        *,
        content: bytes,
        mime_type: str,
        sha256_hex: str,
        tenant_id: str,
        principal_id: str,
    ) -> ReferenceRelayTicket: ...

    def release(self, ticket: ReferenceRelayTicket) -> None: ...


class SignedReferenceRelayStore:
    """Durable short-lived relay storage behind an HTTPS reverse proxy."""

    def __init__(
        self,
        database_path: Path,
        blob_root: Path,
        *,
        public_base_url: str,
        signing_secret: str,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        if not public_base_url.startswith("https://") or public_base_url.endswith("/"):
            raise ReferenceRelayError(
                "reference relay public_base_url must be trimmed HTTPS without trailing slash"
            )
        if not signing_secret or signing_secret != signing_secret.strip():
            raise ReferenceRelayError("reference relay signing secret is invalid")
        if ttl_seconds <= 0 or ttl_seconds > _MAX_TTL_SECONDS:
            raise ReferenceRelayError("reference relay ttl must be within one hour")
        self._database = database_path
        self._blob_root = blob_root
        self._base_url = public_base_url
        self._secret = signing_secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds
        database_path.parent.mkdir(parents=True, exist_ok=True)
        blob_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reference_relay_items ("
                "relay_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, mime_type TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, principal_id TEXT NOT NULL, "
                "expires_at_epoch_s INTEGER NOT NULL, blob_name TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def publish(
        self,
        *,
        content: bytes,
        mime_type: str,
        sha256_hex: str,
        tenant_id: str,
        principal_id: str,
        now_epoch_s: int | None = None,
    ) -> ReferenceRelayTicket:
        _validate_reference_bytes(content, mime_type, sha256_hex)
        _require_identity(tenant_id, "tenant_id")
        _require_identity(principal_id, "principal_id")
        now = int(time.time()) if now_epoch_s is None else now_epoch_s
        expires = now + self._ttl_seconds
        relay_id = secrets.token_urlsafe(24)
        blob_name = f"{relay_id}.image"
        blob_path = self._blob_root / blob_name
        blob_path.write_bytes(content)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO reference_relay_items VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        relay_id,
                        sha256_hex,
                        mime_type,
                        tenant_id,
                        principal_id,
                        expires,
                        blob_name,
                    ),
                )
        except Exception:
            blob_path.unlink(missing_ok=True)
            raise
        signature = self._signature(relay_id, sha256_hex, expires)
        query = urlencode(
            {"expires": str(expires), "sha256": sha256_hex, "signature": signature}
        )
        return ReferenceRelayTicket(
            relay_id=relay_id,
            url=f"{self._base_url}/v1/reference-relay/{relay_id}?{query}",
            sha256=sha256_hex,
            mime_type=mime_type,
            expires_at_epoch_s=expires,
        )

    def resolve(
        self,
        *,
        relay_id: str,
        expires_at_epoch_s: int,
        sha256_hex: str,
        signature: str,
        now_epoch_s: int | None = None,
    ) -> tuple[bytes, str]:
        _require_relay_id(relay_id)
        _require_sha256(sha256_hex)
        if not signature or signature != signature.strip():
            raise ReferenceRelayError("reference relay signature is invalid")
        expected = self._signature(relay_id, sha256_hex, expires_at_epoch_s)
        if not hmac.compare_digest(signature, expected):
            raise ReferenceRelayError("reference relay signature mismatch")
        now = int(time.time()) if now_epoch_s is None else now_epoch_s
        if expires_at_epoch_s < now:
            self.release_id(relay_id)
            raise ReferenceRelayError("reference relay URL expired")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reference_relay_items WHERE relay_id = ?",
                (relay_id,),
            ).fetchone()
        if row is None:
            raise ReferenceRelayError("reference relay item is unavailable")
        if row["expires_at_epoch_s"] != expires_at_epoch_s or row["sha256"] != sha256_hex:
            raise ReferenceRelayError("reference relay URL does not match durable metadata")
        blob_path = self._blob_root / str(row["blob_name"])
        try:
            content = blob_path.read_bytes()
        except OSError as error:
            raise ReferenceRelayError("reference relay blob is unavailable") from error
        if hashlib.sha256(content).hexdigest() != sha256_hex:
            raise ReferenceRelayError("reference relay blob integrity failed")
        return content, str(row["mime_type"])

    def release(self, ticket: ReferenceRelayTicket) -> None:
        self.release_id(ticket.relay_id)

    def release_id(self, relay_id: str) -> None:
        _require_relay_id(relay_id)
        blob_name: str | None = None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT blob_name FROM reference_relay_items WHERE relay_id = ?",
                (relay_id,),
            ).fetchone()
            if row is not None:
                blob_name = str(row["blob_name"])
                connection.execute(
                    "DELETE FROM reference_relay_items WHERE relay_id = ?",
                    (relay_id,),
                )
        if blob_name is not None:
            (self._blob_root / blob_name).unlink(missing_ok=True)

    def purge_expired(self, *, now_epoch_s: int | None = None) -> int:
        now = int(time.time()) if now_epoch_s is None else now_epoch_s
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT relay_id FROM reference_relay_items WHERE expires_at_epoch_s < ?",
                (now,),
            ).fetchall()
        for row in rows:
            self.release_id(str(row["relay_id"]))
        return len(rows)

    def _signature(self, relay_id: str, sha256_hex: str, expires_at_epoch_s: int) -> str:
        material = f"{relay_id}\n{sha256_hex}\n{expires_at_epoch_s}".encode("utf-8")
        return hmac.new(self._secret, material, hashlib.sha256).hexdigest()


class HttpReferenceRelayClient:
    """Upload admitted reference bytes to the trusted relay service."""

    def __init__(
        self,
        *,
        upload_url: str,
        bearer_token: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not upload_url.startswith("https://"):
            raise ReferenceRelayError("reference relay upload URL must use HTTPS")
        if not bearer_token or bearer_token != bearer_token.strip():
            raise ReferenceRelayError("reference relay bearer token is invalid")
        if timeout_seconds <= 0:
            raise ReferenceRelayError("reference relay timeout must be positive")
        self._upload_url = upload_url
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    def publish(
        self,
        *,
        content: bytes,
        mime_type: str,
        sha256_hex: str,
        tenant_id: str,
        principal_id: str,
    ) -> ReferenceRelayTicket:
        _validate_reference_bytes(content, mime_type, sha256_hex)
        _require_identity(tenant_id, "tenant_id")
        _require_identity(principal_id, "principal_id")
        document = json.dumps(
            {
                "content_base64": base64.b64encode(content).decode("ascii"),
                "mime_type": mime_type,
                "sha256": sha256_hex,
                "tenant_id": tenant_id,
                "principal_id": principal_id,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self._upload_url,
            data=document,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status != 201:
                    raise ReferenceRelayError(
                        f"reference relay upload failed with HTTP {response.status}"
                    )
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise ReferenceRelayError("reference relay upload failed") from error
        return _ticket_from_payload(payload, expected_sha256=sha256_hex)

    def release(self, ticket: ReferenceRelayTicket) -> None:
        parsed = urlparse(ticket.url)
        release_url = f"{parsed.scheme}://{parsed.netloc}/v1/reference-relay/{ticket.relay_id}"
        request = urllib.request.Request(
            release_url,
            method="DELETE",
            headers={"Authorization": f"Bearer {self._bearer_token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status not in {200, 204}:
                    raise ReferenceRelayError(
                        f"reference relay release failed with HTTP {response.status}"
                    )
        except (OSError, urllib.error.URLError) as error:
            raise ReferenceRelayError("reference relay release failed") from error


def signed_relay_query(url: str) -> tuple[str, int, str, str]:
    """Parse a relay URL for the public download handler and tests."""

    parsed = urlparse(url)
    relay_id = parsed.path.rsplit("/", 1)[-1]
    query = parse_qs(parsed.query)
    try:
        expires = int(query["expires"][0])
        sha256_hex = query["sha256"][0]
        signature = query["signature"][0]
    except (KeyError, IndexError, ValueError) as error:
        raise ReferenceRelayError("reference relay URL query is incomplete") from error
    return relay_id, expires, sha256_hex, signature


def _ticket_from_payload(payload: object, *, expected_sha256: str) -> ReferenceRelayTicket:
    if not isinstance(payload, dict):
        raise ReferenceRelayError("reference relay response must be an object")
    relay_id = payload.get("relay_id")
    url = payload.get("url")
    sha256_hex = payload.get("sha256")
    mime_type = payload.get("mime_type")
    expires = payload.get("expires_at_epoch_s")
    if not isinstance(relay_id, str):
        raise ReferenceRelayError("reference relay response relay_id is invalid")
    _require_relay_id(relay_id)
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ReferenceRelayError("reference relay response URL is not HTTPS")
    if sha256_hex != expected_sha256:
        raise ReferenceRelayError("reference relay response digest mismatch")
    if not isinstance(mime_type, str) or mime_type not in _ALLOWED_MIME_TYPES:
        raise ReferenceRelayError("reference relay response MIME is invalid")
    if isinstance(expires, bool) or not isinstance(expires, int) or expires <= int(time.time()):
        raise ReferenceRelayError("reference relay response expiry is invalid")
    return ReferenceRelayTicket(relay_id, url, sha256_hex, mime_type, expires)


def _validate_reference_bytes(content: bytes, mime_type: str, sha256_hex: str) -> None:
    if not content or len(content) > _MAX_RELAY_BYTES:
        raise ReferenceRelayError("reference relay image size is invalid")
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise ReferenceRelayError("reference relay MIME type is unsupported")
    _require_sha256(sha256_hex)
    if hashlib.sha256(content).hexdigest() != sha256_hex:
        raise ReferenceRelayError("reference relay SHA-256 does not match bytes")
    if not _mime_magic_matches(content, mime_type):
        raise ReferenceRelayError("reference relay MIME type does not match image bytes")


def _mime_magic_matches(content: bytes, mime_type: str) -> bool:
    if mime_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if mime_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


def _require_identity(value: str, name: str) -> None:
    if not value or value != value.strip() or len(value) > 200:
        raise ReferenceRelayError(f"reference relay {name} is invalid")


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ReferenceRelayError("reference relay SHA-256 is invalid")


def _require_relay_id(value: str) -> None:
    if not value or value != value.strip() or len(value) > 128:
        raise ReferenceRelayError("reference relay id is invalid")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if any(character not in allowed for character in value):
        raise ReferenceRelayError("reference relay id contains invalid characters")
