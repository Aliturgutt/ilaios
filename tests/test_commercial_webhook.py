from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

from services.commercial_access import CommercialAccessError
from services.commercial_webhook import CommercialWebhookVerifier


_SECRET = b"s" * 32
_NOW = datetime(2026, 8, 27, 0, 20, tzinfo=timezone.utc)
_POSITIVE_EVENTS = frozenset({"subscription.activated", "subscription.renewed"})


def _body(**overrides: object) -> bytes:
    payload: dict[str, object] = {
        "event_id": "evt-sub-1",
        "event_type": "subscription.activated",
        "provider_subscription_id": "sub-provider-1",
        "occurred_at": "2026-08-27T00:19:00+00:00",
    }
    payload.update(overrides)
    if payload.get("event_type") in _POSITIVE_EVENTS and "billing_period_end" not in payload:
        payload["billing_period_end"] = "2026-09-27T00:19:00+00:00"
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _signature(body: bytes, *, when: datetime = _NOW, secret: bytes = _SECRET) -> str:
    timestamp = int(when.timestamp())
    digest = hmac.new(
        secret,
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_verified_event_exposes_provider_identity_only() -> None:
    body = _body()
    verified = CommercialWebhookVerifier(_SECRET).verify(
        raw_body=body,
        signature_header=_signature(body),
        now=_NOW,
    )

    assert verified.event_id == "evt-sub-1"
    assert verified.event_type == "subscription.activated"
    assert verified.provider_subscription_id == "sub-provider-1"
    assert verified.billing_period_end == datetime(2026, 9, 27, 0, 19, tzinfo=timezone.utc)
    assert verified.payload_sha256 == hashlib.sha256(body).hexdigest()
    assert verified.signature_timestamp == _NOW


def test_tampered_body_fails_signature_verification() -> None:
    original = _body()
    tampered = _body(provider_subscription_id="sub-attacker")

    with pytest.raises(CommercialAccessError, match="signature is invalid"):
        CommercialWebhookVerifier(_SECRET).verify(
            raw_body=tampered,
            signature_header=_signature(original),
            now=_NOW,
        )


def test_stale_or_future_signature_fails_closed() -> None:
    body = _body()
    signed_times = (
        _NOW - timedelta(seconds=301),
        _NOW + timedelta(seconds=1),
    )
    for signed_at in signed_times:
        with pytest.raises(CommercialAccessError, match="timestamp is outside policy"):
            CommercialWebhookVerifier(_SECRET).verify(
                raw_body=body,
                signature_header=_signature(body, when=signed_at),
                now=_NOW,
            )


def test_malformed_signature_header_fails_closed() -> None:
    body = _body()
    headers = (
        "",
        "t=123",
        "v1=" + "0" * 64,
        "t=123,t=123,v1=" + "0" * 64,
        "t=nope,v1=" + "0" * 64,
        "t=123,v2=" + "0" * 64,
        "t=123,v1=xyz",
    )
    for header in headers:
        with pytest.raises(CommercialAccessError, match="signature"):
            CommercialWebhookVerifier(_SECRET).verify(
                raw_body=body,
                signature_header=header,
                now=_NOW,
            )


def test_payload_cannot_smuggle_canonical_account_authority() -> None:
    body = _body(user_id="user-attacker")

    with pytest.raises(CommercialAccessError, match="payload fields are invalid"):
        CommercialWebhookVerifier(_SECRET).verify(
            raw_body=body,
            signature_header=_signature(body),
            now=_NOW,
        )


def test_positive_events_require_bounded_signed_billing_period() -> None:
    missing_period = json.dumps(
        {
            "event_id": "evt-missing-period",
            "event_type": "subscription.activated",
            "provider_subscription_id": "sub-provider-1",
            "occurred_at": "2026-08-27T00:19:00+00:00",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    invalid_periods = (
        missing_period,
        _body(billing_period_end="2026-08-27T00:18:00+00:00"),
        _body(billing_period_end="2028-01-01T00:19:00+00:00"),
    )
    for body in invalid_periods:
        with pytest.raises(CommercialAccessError, match="billing"):
            CommercialWebhookVerifier(_SECRET).verify(
                raw_body=body,
                signature_header=_signature(body),
                now=_NOW,
            )


def test_negative_event_rejects_positive_billing_period_authority() -> None:
    body = _body(
        event_type="payment.failed",
        billing_period_end="2026-09-27T00:19:00+00:00",
    )

    with pytest.raises(CommercialAccessError, match="not allowed"):
        CommercialWebhookVerifier(_SECRET).verify(
            raw_body=body,
            signature_header=_signature(body),
            now=_NOW,
        )


def test_invalid_provider_event_fields_fail_closed() -> None:
    invalid_payloads: tuple[dict[str, object], ...] = (
        {"event_type": "checkout.admin_override"},
        {"event_id": " "},
        {"provider_subscription_id": ""},
        {"occurred_at": "not-a-time"},
    )
    for overrides in invalid_payloads:
        body = _body(**overrides)
        with pytest.raises(CommercialAccessError):
            CommercialWebhookVerifier(_SECRET).verify(
                raw_body=body,
                signature_header=_signature(body),
                now=_NOW,
            )


def test_wrong_secret_fails_closed() -> None:
    body = _body()

    with pytest.raises(CommercialAccessError, match="signature is invalid"):
        CommercialWebhookVerifier(_SECRET).verify(
            raw_body=body,
            signature_header=_signature(body, secret=b"x" * 32),
            now=_NOW,
        )


def test_weak_secret_and_unsafe_age_policy_are_rejected() -> None:
    with pytest.raises(CommercialAccessError, match="secret is too weak"):
        CommercialWebhookVerifier(b"short")
    with pytest.raises(CommercialAccessError, match="age policy is invalid"):
        CommercialWebhookVerifier(_SECRET, max_signature_age_seconds=0)


def test_invalid_timestamp_range_fails_closed() -> None:
    body = _body()
    header = "t=999999999999999999999999999999,v1=" + "0" * 64

    with pytest.raises(CommercialAccessError, match="timestamp is invalid"):
        CommercialWebhookVerifier(_SECRET).verify(
            raw_body=body,
            signature_header=header,
            now=_NOW,
        )


def test_verifier_does_not_mutate_entitlement_or_accept_account_mapping() -> None:
    body = _body(event_type="payment.failed")
    verified = CommercialWebhookVerifier(_SECRET).verify(
        raw_body=body,
        signature_header=_signature(body),
        now=_NOW,
    )

    assert verified.event_type == "payment.failed"
    assert verified.billing_period_end is None
    assert not hasattr(verified, "tenant_id")
    assert not hasattr(verified, "user_id")
    assert not hasattr(verified, "plan_id")
