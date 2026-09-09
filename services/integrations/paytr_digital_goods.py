"""PayTR checkout/callback adapter for canonical commercial digital goods.

The adapter does not own commerce state, entitlement, approval, or secret values.
It consumes the existing ``CommercialDigitalGoodsExtension`` and opaque secret
references, keeping provider mutation outside the Creative / Document Factory.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol

from services.commercial_access import CommercialAccessError
from services.commercial_digital_goods import (
    CommercialDigitalGoodsExtension,
    DigitalBookOrder,
)
from services.commercial_webhook import VerifiedDigitalPaymentEvent

_PAYTR_TOKEN_URL = "https://www.paytr.com/odeme/api/get-token"
_PAYTR_IFRAME_URL = "https://www.paytr.com/odeme/guvenli/"
_REFERENCE_PREFIXES = ("env://", "kms://", "vault://")
_SUPPORTED_CURRENCIES = frozenset({"TL", "USD", "EUR", "GBP", "RUB"})


class PayTRTransport(Protocol):
    def post_form(self, url: str, fields: Mapping[str, str]) -> Mapping[str, object]: ...


class SecretReferenceResolver(Protocol):
    def resolve(self, reference: str, *, tenant_id: str, purpose: str) -> str: ...


@dataclass(frozen=True, slots=True)
class PayTRSecretReferences:
    merchant_id: str
    merchant_key: str
    merchant_salt: str

    def __post_init__(self) -> None:
        for name, reference in (
            ("merchant_id", self.merchant_id),
            ("merchant_key", self.merchant_key),
            ("merchant_salt", self.merchant_salt),
        ):
            _require_secret_reference(name, reference)


@dataclass(frozen=True, slots=True)
class PayTRCheckoutRequest:
    order_id: str
    tenant_id: str
    user_id: str
    product_id: str
    user_ip: str
    email: str
    user_name: str
    user_address: str
    user_phone: str
    merchant_ok_url: str
    merchant_fail_url: str
    price_minor: int
    currency: str = "TL"
    no_installment: int = 0
    max_installment: int = 0
    test_mode: bool = True


@dataclass(frozen=True, slots=True)
class PayTRCheckout:
    order: DigitalBookOrder
    iframe_token: str
    iframe_url: str
    test_mode: bool


class EnvironmentSecretReferenceResolver:
    """Resolve canonical ``env://`` references without persisting secret values."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = os.environ if environment is None else environment

    def resolve(self, reference: str, *, tenant_id: str, purpose: str) -> str:
        _require_text("tenant_id", tenant_id)
        _require_text("purpose", purpose)
        _require_secret_reference("reference", reference)
        if not reference.startswith("env://"):
            raise CommercialAccessError(
                "configured secret reference requires a runtime KMS/vault resolver"
            )
        name = reference.removeprefix("env://")
        value = self._environment.get(name, "")
        if not value:
            raise CommercialAccessError("configured provider secret reference is unavailable")
        return value


class UrllibPayTRTransport:
    """Small provider transport; governance must authorize callers before use."""

    def post_form(self, url: str, fields: Mapping[str, str]) -> Mapping[str, object]:
        if url != _PAYTR_TOKEN_URL:
            raise CommercialAccessError("PayTR transport destination is not allowlisted")
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(dict(fields)).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
                body = response.read(64 * 1024)
        except OSError as error:
            raise CommercialAccessError("PayTR checkout transport failed") from error
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CommercialAccessError("PayTR checkout response is malformed") from error
        if not isinstance(payload, dict):
            raise CommercialAccessError("PayTR checkout response is malformed")
        return payload


class PayTRDigitalGoodsAdapter:
    """Create PayTR test/live checkout and verify callbacks fail-closed."""

    def __init__(
        self,
        commercial: CommercialDigitalGoodsExtension,
        *,
        secret_references: PayTRSecretReferences,
        secret_resolver: SecretReferenceResolver,
        transport: PayTRTransport,
    ) -> None:
        self._commercial = commercial
        self._secret_references = secret_references
        self._secret_resolver = secret_resolver
        self._transport = transport

    def create_checkout(self, request: PayTRCheckoutRequest, *, now: datetime) -> PayTRCheckout:
        _validate_checkout_request(request)
        _require_time("now", now)
        merchant_id, merchant_key, merchant_salt = self._credentials(request.tenant_id)
        provider_order_id = request.order_id
        order = self._commercial.create_pending_order(
            order_id=request.order_id,
            provider_order_id=provider_order_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            product_id=request.product_id,
            price_minor=request.price_minor,
            currency=_normalize_currency(request.currency),
            now=now,
        )
        basket = base64.b64encode(
            json.dumps(
                [[request.product_id, f"{request.price_minor / 100:.2f}", 1]],
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).decode("ascii")
        test_mode = "1" if request.test_mode else "0"
        currency = _normalize_currency(request.currency)
        hash_text = (
            merchant_id
            + request.user_ip
            + provider_order_id
            + request.email
            + str(request.price_minor)
            + basket
            + str(request.no_installment)
            + str(request.max_installment)
            + currency
            + test_mode
        )
        paytr_token = base64.b64encode(
            hmac.new(
                merchant_key.encode("utf-8"),
                (hash_text + merchant_salt).encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")
        fields = {
            "merchant_id": merchant_id,
            "user_ip": request.user_ip,
            "merchant_oid": provider_order_id,
            "email": request.email,
            "payment_amount": str(request.price_minor),
            "paytr_token": paytr_token,
            "user_basket": basket,
            "debug_on": "1" if request.test_mode else "0",
            "no_installment": str(request.no_installment),
            "max_installment": str(request.max_installment),
            "user_name": request.user_name,
            "user_address": request.user_address,
            "user_phone": request.user_phone,
            "merchant_ok_url": request.merchant_ok_url,
            "merchant_fail_url": request.merchant_fail_url,
            "timeout_limit": "30",
            "currency": currency,
            "test_mode": test_mode,
            "lang": "tr",
        }
        response = self._transport.post_form(_PAYTR_TOKEN_URL, fields)
        if response.get("status") != "success":
            raise CommercialAccessError("PayTR checkout token request was rejected")
        iframe_token = response.get("token")
        if not isinstance(iframe_token, str) or not iframe_token.strip():
            raise CommercialAccessError("PayTR checkout response did not contain a token")
        return PayTRCheckout(
            order=order,
            iframe_token=iframe_token,
            iframe_url=_PAYTR_IFRAME_URL + urllib.parse.quote(iframe_token, safe=""),
            test_mode=request.test_mode,
        )

    def verify_callback(
        self,
        fields: Mapping[str, str],
        *,
        expected_order: DigitalBookOrder,
        now: datetime,
    ) -> VerifiedDigitalPaymentEvent:
        _require_time("now", now)
        required = {"merchant_oid", "status", "total_amount", "hash", "payment_amount", "currency"}
        if not required.issubset(fields):
            raise CommercialAccessError("PayTR callback fields are incomplete")
        merchant_oid = _required_field(fields, "merchant_oid")
        status = _required_field(fields, "status")
        total_amount = _required_field(fields, "total_amount")
        presented_hash = _required_field(fields, "hash")
        payment_amount = _parse_positive_int(_required_field(fields, "payment_amount"), "payment_amount")
        currency = _normalize_currency(_required_field(fields, "currency"))
        if merchant_oid != expected_order.provider_order_id:
            raise CommercialAccessError("PayTR callback order binding does not match")
        if payment_amount != expected_order.price_minor or currency != expected_order.currency:
            raise CommercialAccessError("PayTR callback payment amount does not match canonical order")
        _, merchant_key, merchant_salt = self._credentials(expected_order.tenant_id)
        token_text = merchant_oid + merchant_salt + status + total_amount
        expected_hash = base64.b64encode(
            hmac.new(
                merchant_key.encode("utf-8"),
                token_text.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")
        if not hmac.compare_digest(expected_hash, presented_hash):
            raise CommercialAccessError("PayTR callback signature is invalid")
        if status not in {"success", "failed"}:
            raise CommercialAccessError("PayTR callback payment status is unsupported")
        canonical_payload = json.dumps(
            {
                "merchant_oid": merchant_oid,
                "status": status,
                "total_amount": total_amount,
                "payment_amount": str(payment_amount),
                "currency": currency,
                "hash": presented_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        payload_sha256 = hashlib.sha256(canonical_payload).hexdigest()
        event_type = "payment.succeeded" if status == "success" else "payment.failed"
        return VerifiedDigitalPaymentEvent(
            event_id="paytr:" + payload_sha256,
            event_type=event_type,
            provider_order_id=merchant_oid,
            occurred_at=now,
            payload_sha256=payload_sha256,
            signature_timestamp=now,
        )

    def _credentials(self, tenant_id: str) -> tuple[str, str, str]:
        purpose = "provider-authentication"
        merchant_id = self._secret_resolver.resolve(
            self._secret_references.merchant_id,
            tenant_id=tenant_id,
            purpose=purpose,
        )
        merchant_key = self._secret_resolver.resolve(
            self._secret_references.merchant_key,
            tenant_id=tenant_id,
            purpose=purpose,
        )
        merchant_salt = self._secret_resolver.resolve(
            self._secret_references.merchant_salt,
            tenant_id=tenant_id,
            purpose=purpose,
        )
        for name, value in (
            ("merchant_id", merchant_id),
            ("merchant_key", merchant_key),
            ("merchant_salt", merchant_salt),
        ):
            _require_text(name, value)
        return merchant_id, merchant_key, merchant_salt


def _validate_checkout_request(request: PayTRCheckoutRequest) -> None:
    if not isinstance(request, PayTRCheckoutRequest):
        raise CommercialAccessError("PayTR checkout request is invalid")
    for name in (
        "order_id",
        "tenant_id",
        "user_id",
        "product_id",
        "user_ip",
        "email",
        "user_name",
        "user_address",
        "user_phone",
        "merchant_ok_url",
        "merchant_fail_url",
    ):
        _require_text(name, getattr(request, name))
    if not isinstance(request.price_minor, int) or isinstance(request.price_minor, bool) or request.price_minor <= 0:
        raise CommercialAccessError("PayTR checkout price must be a positive minor-unit amount")
    if request.no_installment not in {0, 1}:
        raise CommercialAccessError("PayTR no_installment value is invalid")
    if request.max_installment not in {0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}:
        raise CommercialAccessError("PayTR max_installment value is invalid")
    _normalize_currency(request.currency)


def _normalize_currency(value: str) -> str:
    _require_text("currency", value)
    normalized = value.upper()
    if normalized not in _SUPPORTED_CURRENCIES:
        raise CommercialAccessError("PayTR currency is unsupported")
    return normalized


def _required_field(fields: Mapping[str, str], name: str) -> str:
    value = fields.get(name, "")
    _require_text(name, value)
    return value


def _parse_positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise CommercialAccessError(f"PayTR callback {name} is invalid") from error
    if parsed <= 0:
        raise CommercialAccessError(f"PayTR callback {name} is invalid")
    return parsed


def _require_secret_reference(name: str, reference: str) -> None:
    _require_text(name, reference)
    if not reference.startswith(_REFERENCE_PREFIXES) or any(character.isspace() for character in reference):
        raise CommercialAccessError(f"{name} must be an opaque secret reference")


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError(f"{name} must be non-blank and trimmed")


def _require_time(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CommercialAccessError(f"{name} must be timezone-aware")


__all__ = [
    "EnvironmentSecretReferenceResolver",
    "PayTRCheckout",
    "PayTRCheckoutRequest",
    "PayTRDigitalGoodsAdapter",
    "PayTRSecretReferences",
    "PayTRTransport",
    "SecretReferenceResolver",
    "UrllibPayTRTransport",
]
