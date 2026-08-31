from __future__ import annotations

import hashlib

import pytest

from services.cloudflare_reference_relay import _ticket_from_cloudflare_payload
from services.reference_relay import ReferenceRelayError


def test_cloudflare_payload_maps_fetch_url_to_canonical_ticket() -> None:
    content = b"\x89PNG\r\n\x1a\n" + b"ilaios"
    digest = hashlib.sha256(content).hexdigest()
    ticket = _ticket_from_cloudflare_payload(
        {
            "relay_id": "relay_1234567890123456",
            "fetch_url": "https://relay.example/v1/reference-relay/relay_1234567890123456?expires=2000000000&sig=" + "a" * 64,
            "sha256": digest,
            "mime_type": "image/png",
            "expires_at_epoch_s": 2000000000,
            "ttl_seconds": 1800,
        },
        expected_sha256=digest,
    )

    assert ticket.relay_id == "relay_1234567890123456"
    assert ticket.url.startswith("https://relay.example/v1/reference-relay/")
    assert ticket.sha256 == digest
    assert ticket.mime_type == "image/png"
    assert ticket.expires_at_epoch_s == 2000000000


def test_cloudflare_payload_fails_closed_on_digest_mismatch() -> None:
    with pytest.raises(ReferenceRelayError, match="digest mismatch"):
        _ticket_from_cloudflare_payload(
            {
                "relay_id": "relay_1234567890123456",
                "fetch_url": "https://relay.example/v1/reference-relay/relay_1234567890123456?expires=2000000000&sig=" + "a" * 64,
                "sha256": "b" * 64,
                "mime_type": "image/png",
                "expires_at_epoch_s": 2000000000,
            },
            expected_sha256="a" * 64,
        )
