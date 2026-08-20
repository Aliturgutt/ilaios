"""Cloudflare R2+D1 reference relay adapter for the canonical ReferenceRelay protocol.

The adapter preserves the existing governed runtime boundary: only already-admitted
reference bytes are published, tenant/principal identity remains server-side, and
cleanup fails closed. The deployed Worker contract is raw image bytes with identity
headers and a short-lived signed fetch URL in ``fetch_url``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from threading import Lock
from urllib.parse import urlparse

from services.reference_relay import (
    ReferenceRelayError,
    ReferenceRelayTicket,
    _require_identity,
    _ticket_from_cloudflare_payload,
    _validate_reference_bytes,
)


class CloudflareReferenceRelayClient:
    """Publish admitted references to the Cloudflare Worker R2+D1 relay."""

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
        self._identities: dict[str, tuple[str, str]] = {}
        self._lock = Lock()

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
        request = urllib.request.Request(
            self._upload_url,
            data=content,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": mime_type,
                "Accept": "application/json",
                "X-ILAIOS-Tenant-Id": tenant_id,
                "X-ILAIOS-Principal-Id": principal_id,
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
        ticket = _ticket_from_cloudflare_payload(payload, expected_sha256=sha256_hex)
        with self._lock:
            self._identities[ticket.relay_id] = (tenant_id, principal_id)
        return ticket

    def release(self, ticket: ReferenceRelayTicket) -> None:
        with self._lock:
            identity = self._identities.get(ticket.relay_id)
        if identity is None:
            raise ReferenceRelayError("reference relay cleanup identity is unavailable")
        tenant_id, principal_id = identity
        parsed = urlparse(ticket.url)
        release_url = f"{parsed.scheme}://{parsed.netloc}/v1/reference-relay/{ticket.relay_id}"
        request = urllib.request.Request(
            release_url,
            method="DELETE",
            headers={
                "Authorization": f"Bearer {self._bearer_token}",
                "Accept": "application/json",
                "X-ILAIOS-Tenant-Id": tenant_id,
                "X-ILAIOS-Principal-Id": principal_id,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status not in {200, 204}:
                    raise ReferenceRelayError(
                        f"reference relay release failed with HTTP {response.status}"
                    )
        except (OSError, urllib.error.URLError) as error:
            raise ReferenceRelayError("reference relay release failed") from error
        with self._lock:
            self._identities.pop(ticket.relay_id, None)

    def ready(self) -> bool:
        parsed = urlparse(self._upload_url)
        ready_url = f"{parsed.scheme}://{parsed.netloc}/health/ready"
        request = urllib.request.Request(ready_url, method="GET", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status != 200:
                    return False
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return False
        return isinstance(payload, dict) and payload.get("status") == "ready"
