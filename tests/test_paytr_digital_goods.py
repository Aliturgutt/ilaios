from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest

from services.book_renderers import render_book_package
from services.commercial_access import CommercialAccessError, CommercialAccessStore
from services.commercial_digital_goods import CommercialDigitalGoodsExtension, DigitalOrderState
from services.creative_document_factory import (
    BookChapter,
    BookMetadata,
    CreativeDocumentFactory,
)
from services.integrations.paytr_digital_goods import (
    EnvironmentSecretReferenceResolver,
    PayTRCheckoutRequest,
    PayTRDigitalGoodsAdapter,
    PayTRSecretReferences,
)
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore

_ENV = {
    "PAYTR_MERCHANT_ID": "merchant-1",
    "PAYTR_MERCHANT_KEY": "merchant-key-abcdefghijklmnopqrstuvwxyz",
    "PAYTR_MERCHANT_SALT": "merchant-salt-abcdefghijklmnopqrstuvwxyz",
}


class _Transport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def post_form(self, url: str, fields: Mapping[str, str]) -> Mapping[str, object]:
        self.calls.append((url, dict(fields)))
        return {"status": "success", "token": "iframe-token-1"}


def _commercial(tmp_path: Path) -> CommercialDigitalGoodsExtension:
    credits = ManagedCreditLedgerStore(tmp_path / "credits")
    access = CommercialAccessStore(tmp_path / "commercial", credits)
    return CommercialDigitalGoodsExtension(access)


def _register_product(
    extension: CommercialDigitalGoodsExtension,
    now: datetime,
    *,
    currency: str = "TRY",
) -> None:
    factory = CreativeDocumentFactory()
    factory.compose_book(
        "book-paytr",
        metadata=BookMetadata(
            title="PayTR Digital Book",
            author="ILAIOS",
            publisher="ILAIOS",
            language="tr",
            edition="1",
            publication_date="2026-09-09",
            description="PayTR governed digital delivery fixture.",
            keywords=("book", "paytr"),
        ),
        chapters=(
            BookChapter(
                chapter_id="chapter-1",
                title="Giriş",
                body="PayTR test fixture.",
                factual=False,
                claim_ids=(),
                citations=(),
                editorial_evidence_ref="editorial://book-paytr/chapter-1",
                originality_evidence_ref="originality://book-paytr/chapter-1",
            ),
        ),
        research_projections=(),
        build_version="1",
    )
    book = factory.approve_book("book-paytr")
    package = render_book_package(book)
    extension.register_approved_book_product(
        product_id="product-paytr",
        book=book,
        export=package.export_manifest,
        price_minor=129900,
        currency=currency,
        now=now,
    )


def _adapter(
    extension: CommercialDigitalGoodsExtension,
) -> tuple[PayTRDigitalGoodsAdapter, _Transport]:
    transport = _Transport()
    adapter = PayTRDigitalGoodsAdapter(
        extension,
        secret_references=PayTRSecretReferences(
            merchant_id="env://PAYTR_MERCHANT_ID",
            merchant_key="env://PAYTR_MERCHANT_KEY",
            merchant_salt="env://PAYTR_MERCHANT_SALT",
        ),
        secret_resolver=EnvironmentSecretReferenceResolver(_ENV),
        transport=transport,
    )
    return adapter, transport


def _checkout_request(*, currency: str = "TRY", locale: str = "tr") -> PayTRCheckoutRequest:
    return PayTRCheckoutRequest(
        order_id="order-paytr-1",
        tenant_id="tenant-1",
        user_id="user-1",
        product_id="product-paytr",
        user_ip="203.0.113.5",
        email="buyer@example.com",
        user_name="Test Buyer",
        user_address="Test address",
        user_phone="+905551112233",
        merchant_ok_url="https://example.test/order/success",
        merchant_fail_url="https://example.test/order/fail",
        price_minor=129900,
        currency=currency,
        locale=locale,
        test_mode=True,
    )


def _callback_fields(
    *,
    status: str,
    payment_amount: int = 129900,
    provider_currency: str = "TL",
) -> dict[str, str]:
    merchant_oid = "order-paytr-1"
    total_amount = str(payment_amount)
    token_text = merchant_oid + _ENV["PAYTR_MERCHANT_SALT"] + status + total_amount
    signature = base64.b64encode(
        hmac.new(
            _ENV["PAYTR_MERCHANT_KEY"].encode(),
            token_text.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()
    return {
        "merchant_oid": merchant_oid,
        "status": status,
        "total_amount": total_amount,
        "payment_amount": str(payment_amount),
        "currency": provider_currency,
        "hash": signature,
        "test_mode": "1",
    }


def test_checkout_defaults_to_turkish_try_and_uses_opaque_secret_references(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now)
    adapter, transport = _adapter(extension)

    checkout = adapter.create_checkout(_checkout_request(), now=now)

    assert checkout.order.state is DigitalOrderState.PENDING
    assert checkout.order.currency == "TRY"
    assert checkout.test_mode is True
    assert checkout.iframe_url.endswith("iframe-token-1")
    assert len(transport.calls) == 1
    _, fields = transport.calls[0]
    assert fields["payment_amount"] == "129900"
    assert fields["currency"] == "TL"
    assert fields["lang"] == "tr"
    assert fields["test_mode"] == "1"
    serialized = repr(fields)
    assert _ENV["PAYTR_MERCHANT_KEY"] not in serialized
    assert _ENV["PAYTR_MERCHANT_SALT"] not in serialized


def test_english_selection_uses_usd_and_english_checkout(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now, currency="USD")
    adapter, transport = _adapter(extension)

    checkout = adapter.create_checkout(_checkout_request(currency="USD", locale="en"), now=now)

    assert checkout.order.currency == "USD"
    _, fields = transport.calls[0]
    assert fields["currency"] == "USD"
    assert fields["lang"] == "en"


def test_locale_currency_mismatch_fails_closed_before_provider_call(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now, currency="USD")
    adapter, transport = _adapter(extension)

    with pytest.raises(CommercialAccessError, match="locale and currency"):
        adapter.create_checkout(_checkout_request(currency="USD", locale="tr"), now=now)
    assert transport.calls == []


def test_client_price_change_is_rejected_before_provider_call(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now)
    adapter, transport = _adapter(extension)
    changed = replace(_checkout_request(), price_minor=1)

    with pytest.raises(CommercialAccessError, match="server product price"):
        adapter.create_checkout(changed, now=now)
    assert transport.calls == []


def test_invalid_callback_signature_or_amount_cannot_grant_entitlement(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now)
    adapter, _ = _adapter(extension)
    checkout = adapter.create_checkout(_checkout_request(), now=now)

    bad_signature = _callback_fields(status="success")
    bad_signature["hash"] = "invalid"
    with pytest.raises(CommercialAccessError, match="signature"):
        adapter.verify_callback(bad_signature, expected_order=checkout.order, now=now)

    wrong_amount = _callback_fields(status="success", payment_amount=1)
    with pytest.raises(CommercialAccessError, match="amount"):
        adapter.verify_callback(wrong_amount, expected_order=checkout.order, now=now)

    with pytest.raises(CommercialAccessError, match="paid digital order"):
        extension.issue_download_authorization(
            order_id=checkout.order.order_id,
            tenant_id=checkout.order.tenant_id,
            user_id=checkout.order.user_id,
            now=now,
        )


def test_verified_success_is_idempotent_and_creates_controlled_delivery(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now)
    adapter, _ = _adapter(extension)
    checkout = adapter.create_checkout(_checkout_request(), now=now)
    fields = _callback_fields(status="success")

    event = adapter.verify_callback(fields, expected_order=checkout.order, now=now + timedelta(seconds=1))
    first = extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=1))
    repeated = extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=2))

    assert first.state is DigitalOrderState.PAID
    assert repeated == first
    authorization = extension.issue_download_authorization(
        order_id=first.order_id,
        tenant_id=first.tenant_id,
        user_id=first.user_id,
        now=now + timedelta(seconds=3),
        ttl=timedelta(minutes=1),
    )
    assert extension.authorize_download(
        token=authorization.token,
        tenant_id=first.tenant_id,
        user_id=first.user_id,
        now=now + timedelta(seconds=4),
    ).product_id == "product-paytr"


def test_failed_payment_never_creates_download_entitlement(tmp_path: Path) -> None:
    now = datetime(2026, 9, 9, 5, 0, tzinfo=timezone.utc)
    extension = _commercial(tmp_path)
    _register_product(extension, now)
    adapter, _ = _adapter(extension)
    checkout = adapter.create_checkout(_checkout_request(), now=now)
    event = adapter.verify_callback(
        _callback_fields(status="failed"),
        expected_order=checkout.order,
        now=now + timedelta(seconds=1),
    )
    failed = extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=1))

    assert failed.state is DigitalOrderState.FAILED
    with pytest.raises(CommercialAccessError, match="paid digital order"):
        extension.issue_download_authorization(
            order_id=failed.order_id,
            tenant_id=failed.tenant_id,
            user_id=failed.user_id,
            now=now + timedelta(seconds=2),
        )


def test_non_env_reference_fails_closed_without_runtime_resolver() -> None:
    resolver = EnvironmentSecretReferenceResolver(_ENV)
    with pytest.raises(CommercialAccessError, match="KMS/vault"):
        resolver.resolve(
            "vault://tenant-1/paytr-key",
            tenant_id="tenant-1",
            purpose="provider-authentication",
        )
