"""Provider-neutral signed webhook verification for commercial lifecycle events.

This boundary authenticates external commercial subscription events, but it does not
select an ILAIOS user/tenant. Canonical account/plan authority remains the server-side
provider-subscription binding. Positive subscription events may carry only bounded,
signed billing-period validity used by that existing binding to project entitlement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from services.commercial_access import CommercialAccessError


_MAX_WEBHOOK_BODY_BYTES = 64 * 1024
_DEFAULT_MAX_SIGNATURE_AGE_SECONDS = 300
MAX_COMMERCIAL_BILLING_PERIOD_SECONDS = 400 * 24 * 60 * 60
_POSITIVE_EVENT_TYPES = frozenset({"subscription.activated", "subscription.renewed"})
_ALLOWED_EVENT_TYPES = frozenset(
    {
        *_POSITIVE_EVENT_TYPES,
        "subscription.suspended",
        "subscription.cancelled",
        "payment.failed",
        "payment.refunded",
    }
)
_REQUIRED_PAYLOAD_KEYS = frozenset(
    {"event_id", "event_type", "provider_subscription_id", "occurred_at"}
)
_OPTIONAL_PAYLOAD_KEYS = frozenset({"billing_period_end"})


@dataclass(frozen=True, slots=True)
class VerifiedCommercialWebhookEvent:
    """Cryptographically verified provider event with no canonical-account authority."""

    event_id: str
    event_type: str
    provider_subscription_id: str
    occurred_at: datetime
    payload_sha256: str
    signature_timestamp: datetime
    billing_period_end: datetime | None = None


class CommercialWebhookVerifier:
    """Verify HMAC-signed commercial events before any billing-state mutation."""

    def __init__(
        self,
        signing_secret: bytes,
        *,
        max_signature_age_seconds: int = _DEFAULT_MAX_SIGNATURE_AGE_SECONDS,
    ) -> None:
        if not isinstance(signing_secret, bytes) or len(signing_secret) < 32:
            raise CommercialAccessError("commercial webhook signing secret is too weak")
        if (
            not isinstance(max_signature_age_seconds, int)
            or isinstance(max_signature_age_seconds, bool)
            or max_signature_age_seconds < 30
            or max_signature_age_seconds > 900
        ):
            raise CommercialAccessError("commercial webhook signature age policy is invalid")
        self._signing_secret = signing_secret
        self._max_signature_age_seconds = max_signature_age_seconds

    def verify(
        self,
        *,
        raw_body: bytes,
        signature_header: str,
        now: datetime,
    ) -> VerifiedCommercialWebhookEvent:
        """Return a verified provider event or fail closed without side effects."""

        _require_aware_time("now", now)
        if not isinstance(raw_body, bytes) or not raw_body:
            raise CommercialAccessError("commercial webhook body is required")
        if len(raw_body) > _MAX_WEBHOOK_BODY_BYTES:
            raise CommercialAccessError("commercial webhook body exceeds size limit")

        timestamp_seconds, presented_signature = _parse_signature_header(signature_header)
        try:
            signature_time = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise CommercialAccessError(
                "commercial webhook signature timestamp is invalid"
            ) from error
        age_seconds = (now.astimezone(timezone.utc) - signature_time).total_seconds()
        if age_seconds < 0 or age_seconds > self._max_signature_age_seconds:
            raise CommercialAccessError("commercial webhook signature timestamp is outside policy")

        signed_payload = str(timestamp_seconds).encode("ascii") + b"." + raw_body
        expected_signature = hmac.new(
            self._signing_secret,
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, presented_signature):
            raise CommercialAccessError("commercial webhook signature is invalid")

        payload = _parse_payload(raw_body)
        event_id = _required_text(payload, "event_id")
        event_type = _required_text(payload, "event_type")
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise CommercialAccessError("commercial webhook event type is unsupported")
        provider_subscription_id = _required_text(payload, "provider_subscription_id")
        occurred_at = _parse_event_time("occurred_at", _required_text(payload, "occurred_at"))
        billing_period_end = _billing_period_end(
            payload=payload,
            event_type=event_type,
            occurred_at=occurred_at,
        )

        return VerifiedCommercialWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            provider_subscription_id=provider_subscription_id,
            occurred_at=occurred_at,
            payload_sha256=hashlib.sha256(raw_body).hexdigest(),
            signature_timestamp=signature_time,
            billing_period_end=billing_period_end,
        )


def _parse_signature_header(value: str) -> tuple[int, str]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError("commercial webhook signature header is invalid")
    fields: dict[str, str] = {}
    for part in value.split(","):
        name, separator, item = part.partition("=")
        if not separator or name not in {"t", "v1"} or not item or name in fields:
            raise CommercialAccessError("commercial webhook signature header is invalid")
        fields[name] = item
    if set(fields) != {"t", "v1"}:
        raise CommercialAccessError("commercial webhook signature header is invalid")
    try:
        timestamp_seconds = int(fields["t"])
    except ValueError as error:
        raise CommercialAccessError("commercial webhook signature timestamp is invalid") from error
    if timestamp_seconds <= 0:
        raise CommercialAccessError("commercial webhook signature timestamp is invalid")
    signature = fields["v1"]
    if len(signature) != 64:
        raise CommercialAccessError("commercial webhook signature is invalid")
    try:
        bytes.fromhex(signature)
    except ValueError as error:
        raise CommercialAccessError("commercial webhook signature is invalid") from error
    return timestamp_seconds, signature.lower()


def _parse_payload(raw_body: bytes) -> dict[str, object]:
    try:
        decoded = raw_body.decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CommercialAccessError("commercial webhook payload is malformed") from error
    if not isinstance(payload, dict):
        raise CommercialAccessError("commercial webhook payload must be an object")
    keys = set(payload)
    if not _REQUIRED_PAYLOAD_KEYS.issubset(keys) or not keys.issubset(
        _REQUIRED_PAYLOAD_KEYS | _OPTIONAL_PAYLOAD_KEYS
    ):
        raise CommercialAccessError("commercial webhook payload fields are invalid")
    return payload


def _required_text(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError(f"commercial webhook {name} is invalid")
    if len(value) > 256:
        raise CommercialAccessError(f"commercial webhook {name} is too long")
    return value


def _billing_period_end(
    *,
    payload: dict[str, object],
    event_type: str,
    occurred_at: datetime,
) -> datetime | None:
    has_period = "billing_period_end" in payload
    if event_type not in _POSITIVE_EVENT_TYPES:
        if has_period:
            raise CommercialAccessError(
                "commercial webhook billing_period_end is not allowed for this event type"
            )
        return None
    if not has_period:
        raise CommercialAccessError(
            "commercial webhook billing_period_end is required for positive subscription events"
        )
    period_end = _parse_event_time(
        "billing_period_end",
        _required_text(payload, "billing_period_end"),
    )
    period_seconds = (period_end - occurred_at).total_seconds()
    if period_seconds <= 0 or period_seconds > MAX_COMMERCIAL_BILLING_PERIOD_SECONDS:
        raise CommercialAccessError("commercial webhook billing period is outside policy")
    return period_end


def _parse_event_time(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CommercialAccessError(f"commercial webhook {name} is invalid") from error
    _require_aware_time(name, parsed)
    return parsed


def _require_aware_time(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CommercialAccessError(f"commercial webhook {name} must be timezone-aware")


__all__ = [
    "CommercialWebhookVerifier",
    "MAX_COMMERCIAL_BILLING_PERIOD_SECONDS",
    "VerifiedCommercialWebhookEvent",
]
