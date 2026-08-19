from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.reference_relay import (
    ReferenceRelayError,
    SignedReferenceRelayStore,
    signed_relay_query,
)

_PNG = b"\x89PNG\r\n\x1a\n" + b"ilaios-native-reference"


def _store(tmp_path: Path) -> SignedReferenceRelayStore:
    return SignedReferenceRelayStore(
        tmp_path / "relay.sqlite3",
        tmp_path / "blobs",
        public_base_url="https://relay.ilaios.test",
        signing_secret="test-signing-secret",
        ttl_seconds=300,
    )


def test_signed_relay_round_trip_preserves_exact_bytes_and_digest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    digest = hashlib.sha256(_PNG).hexdigest()
    ticket = store.publish(
        content=_PNG,
        mime_type="image/png",
        sha256_hex=digest,
        tenant_id="tenant-1",
        principal_id="user-1",
        now_epoch_s=1000,
    )

    assert ticket.url.startswith("https://relay.ilaios.test/v1/reference-relay/")
    assert "tenant-1" not in ticket.url
    assert "user-1" not in ticket.url
    relay_id, expires, sha256_hex, signature = signed_relay_query(ticket.url)
    content, mime_type = store.resolve(
        relay_id=relay_id,
        expires_at_epoch_s=expires,
        sha256_hex=sha256_hex,
        signature=signature,
        now_epoch_s=1001,
    )
    assert content == _PNG
    assert mime_type == "image/png"
    assert sha256_hex == digest


def test_signed_relay_rejects_tampering_and_expiry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    digest = hashlib.sha256(_PNG).hexdigest()
    ticket = store.publish(
        content=_PNG,
        mime_type="image/png",
        sha256_hex=digest,
        tenant_id="tenant-1",
        principal_id="user-1",
        now_epoch_s=1000,
    )
    relay_id, expires, sha256_hex, signature = signed_relay_query(ticket.url)

    with pytest.raises(ReferenceRelayError, match="signature mismatch"):
        store.resolve(
            relay_id=relay_id,
            expires_at_epoch_s=expires,
            sha256_hex=sha256_hex,
            signature="0" * 64,
            now_epoch_s=1001,
        )

    with pytest.raises(ReferenceRelayError, match="expired"):
        store.resolve(
            relay_id=relay_id,
            expires_at_epoch_s=expires,
            sha256_hex=sha256_hex,
            signature=signature,
            now_epoch_s=expires + 1,
        )


def test_signed_relay_release_removes_public_capability(tmp_path: Path) -> None:
    store = _store(tmp_path)
    digest = hashlib.sha256(_PNG).hexdigest()
    ticket = store.publish(
        content=_PNG,
        mime_type="image/png",
        sha256_hex=digest,
        tenant_id="tenant-1",
        principal_id="user-1",
        now_epoch_s=1000,
    )
    relay_id, expires, sha256_hex, signature = signed_relay_query(ticket.url)

    store.release(ticket)
    with pytest.raises(ReferenceRelayError, match="unavailable"):
        store.resolve(
            relay_id=relay_id,
            expires_at_epoch_s=expires,
            sha256_hex=sha256_hex,
            signature=signature,
            now_epoch_s=1001,
        )


def test_signed_relay_rejects_wrong_digest_mime_and_non_https_base(tmp_path: Path) -> None:
    digest = hashlib.sha256(_PNG).hexdigest()
    with pytest.raises(ReferenceRelayError, match="public_base_url"):
        SignedReferenceRelayStore(
            tmp_path / "bad.sqlite3",
            tmp_path / "bad-blobs",
            public_base_url="http://relay.example",
            signing_secret="secret",
        )

    store = _store(tmp_path)
    with pytest.raises(ReferenceRelayError, match="SHA-256 does not match"):
        store.publish(
            content=_PNG,
            mime_type="image/png",
            sha256_hex="a" * 64,
            tenant_id="tenant-1",
            principal_id="user-1",
        )
    with pytest.raises(ReferenceRelayError, match="MIME type does not match"):
        store.publish(
            content=_PNG,
            mime_type="image/jpeg",
            sha256_hex=digest,
            tenant_id="tenant-1",
            principal_id="user-1",
        )
