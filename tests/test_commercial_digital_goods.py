from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.book_renderers import render_book_package
from services.commercial_access import CommercialAccessError, CommercialAccessStore
from services.commercial_digital_goods import (
    CommercialDigitalGoodsExtension,
    DigitalBookProduct,
    DigitalOrderState,
)
from services.commercial_webhook import (
    CommercialWebhookVerifier,
    VerifiedDigitalPaymentEvent,
)
from services.creative_document_factory import (
    BookChapter,
    BookManifest,
    BookMetadata,
    CreativeDocumentFactory,
)
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore


_SECRET = b"d" * 32


def _commercial(tmp_path: Path) -> CommercialDigitalGoodsExtension:
    credits = ManagedCreditLedgerStore(tmp_path / "credits")
    access = CommercialAccessStore(tmp_path / "commercial", credits)
    return CommercialDigitalGoodsExtension(access)


def _book(*, approved: bool = True) -> BookManifest:
    factory = CreativeDocumentFactory()
    manifest = factory.compose_book(
        "book-1",
        metadata=BookMetadata(
            title="Governed Digital Book",
            author="ILAIOS",
            publisher="ILAIOS",
            language="en",
            edition="1",
            publication_date="2026-09-08",
            description="Digital sales authority fixture.",
            keywords=("digital", "book"),
        ),
        chapters=(
            BookChapter(
                chapter_id="chapter-1",
                title="Introduction",
                body="A non-factual editorial chapter for the sales authority fixture.",
                factual=False,
                claim_ids=(),
                citations=(),
                editorial_evidence_ref="editorial://book-1/chapter-1",
                originality_evidence_ref="originality://book-1/chapter-1",
            ),
        ),
        research_projections=(),
        build_version="1",
    )
    if approved:
        manifest = factory.approve_book("book-1")
    return manifest


def _registered_product(
    extension: CommercialDigitalGoodsExtension, now: datetime
) -> DigitalBookProduct:
    book = _book()
    package = render_book_package(book)
    return extension.register_approved_book_product(
        product_id="product-1",
        book=book,
        export=package.export_manifest,
        price_minor=1299,
        currency="USD",
        now=now,
    )


def _signed_payment_event(
    *,
    event_id: str,
    event_type: str,
    provider_order_id: str,
    now: datetime,
) -> VerifiedDigitalPaymentEvent:
    payload = json.dumps(
        {
            "event_id": event_id,
            "event_type": event_type,
            "provider_order_id": provider_order_id,
            "occurred_at": now.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    timestamp = int(now.timestamp())
    signature = hmac.new(
        _SECRET,
        str(timestamp).encode("ascii") + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    return CommercialWebhookVerifier(_SECRET).verify_digital_payment(
        raw_body=payload,
        signature_header=f"t={timestamp},v1={signature}",
        now=now,
    )


def test_unapproved_or_mismatched_book_export_cannot_be_sold(tmp_path: Path) -> None:
    extension = _commercial(tmp_path)
    now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    unapproved = _book(approved=False)
    approved = _book()
    export = render_book_package(approved).export_manifest

    with pytest.raises(CommercialAccessError, match="unapproved book"):
        extension.register_approved_book_product(
            product_id="product-1",
            book=unapproved,
            export=export,
            price_minor=1299,
            currency="USD",
            now=now,
        )

    tampered = type(export)(
        book_id=export.book_id,
        title=export.title,
        build_version=export.build_version,
        book_content_sha256="0" * 64,
        pdf_sha256=export.pdf_sha256,
        epub_sha256=export.epub_sha256,
        cover_sha256=export.cover_sha256,
        provenance_sha256=export.provenance_sha256,
        source_provenance_map=export.source_provenance_map,
    )
    with pytest.raises(CommercialAccessError, match="content hash"):
        extension.register_approved_book_product(
            product_id="product-2",
            book=approved,
            export=tampered,
            price_minor=1299,
            currency="USD",
            now=now,
        )


def test_server_price_binding_rejects_client_price_change(tmp_path: Path) -> None:
    extension = _commercial(tmp_path)
    now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    _registered_product(extension, now)

    with pytest.raises(CommercialAccessError, match="server product price"):
        extension.create_pending_order(
            order_id="order-1",
            provider_order_id="provider-order-1",
            tenant_id="tenant-1",
            user_id="user-1",
            product_id="product-1",
            price_minor=1,
            currency="USD",
            now=now,
        )


def test_verified_payment_grants_download_and_refund_revokes_it(tmp_path: Path) -> None:
    extension = _commercial(tmp_path)
    now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    _registered_product(extension, now)
    order = extension.create_pending_order(
        order_id="order-1",
        provider_order_id="provider-order-1",
        tenant_id="tenant-1",
        user_id="user-1",
        product_id="product-1",
        price_minor=1299,
        currency="USD",
        now=now,
    )
    assert order.state is DigitalOrderState.PENDING
    with pytest.raises(CommercialAccessError, match="paid digital order"):
        extension.issue_download_authorization(
            order_id=order.order_id,
            tenant_id=order.tenant_id,
            user_id=order.user_id,
            now=now,
        )

    paid_event = _signed_payment_event(
        event_id="evt-paid-1",
        event_type="payment.succeeded",
        provider_order_id=order.provider_order_id,
        now=now + timedelta(seconds=5),
    )
    paid = extension.apply_verified_payment_event(event=paid_event, now=now + timedelta(seconds=5))
    assert paid.state is DigitalOrderState.PAID
    authorization = extension.issue_download_authorization(
        order_id=order.order_id,
        tenant_id=order.tenant_id,
        user_id=order.user_id,
        now=now + timedelta(seconds=6),
    )
    product = extension.authorize_download(
        token=authorization.token,
        tenant_id=order.tenant_id,
        user_id=order.user_id,
        now=now + timedelta(seconds=7),
    )
    assert product.product_id == "product-1"

    refund_event = _signed_payment_event(
        event_id="evt-refund-1",
        event_type="payment.refunded",
        provider_order_id=order.provider_order_id,
        now=now + timedelta(seconds=8),
    )
    refunded = extension.apply_verified_payment_event(
        event=refund_event,
        now=now + timedelta(seconds=8),
    )
    assert refunded.state is DigitalOrderState.REVOKED
    with pytest.raises(CommercialAccessError, match="revoked"):
        extension.authorize_download(
            token=authorization.token,
            tenant_id=order.tenant_id,
            user_id=order.user_id,
            now=now + timedelta(seconds=9),
        )


def test_verified_payment_event_is_idempotent_and_conflicts_fail(tmp_path: Path) -> None:
    extension = _commercial(tmp_path)
    now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    _registered_product(extension, now)
    extension.create_pending_order(
        order_id="order-1",
        provider_order_id="provider-order-1",
        tenant_id="tenant-1",
        user_id="user-1",
        product_id="product-1",
        price_minor=1299,
        currency="USD",
        now=now,
    )
    event = _signed_payment_event(
        event_id="evt-paid-1",
        event_type="payment.succeeded",
        provider_order_id="provider-order-1",
        now=now + timedelta(seconds=1),
    )
    first = extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=1))
    repeated = extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=2))
    assert repeated == first

    conflicting = _signed_payment_event(
        event_id="evt-paid-1",
        event_type="payment.refunded",
        provider_order_id="provider-order-1",
        now=now + timedelta(seconds=3),
    )
    with pytest.raises(CommercialAccessError, match="conflicts"):
        extension.apply_verified_payment_event(event=conflicting, now=now + timedelta(seconds=3))


def test_download_is_principal_bound_and_short_lived(tmp_path: Path) -> None:
    extension = _commercial(tmp_path)
    now = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
    _registered_product(extension, now)
    extension.create_pending_order(
        order_id="order-1",
        provider_order_id="provider-order-1",
        tenant_id="tenant-1",
        user_id="user-1",
        product_id="product-1",
        price_minor=1299,
        currency="USD",
        now=now,
    )
    event = _signed_payment_event(
        event_id="evt-paid-1",
        event_type="payment.succeeded",
        provider_order_id="provider-order-1",
        now=now + timedelta(seconds=1),
    )
    extension.apply_verified_payment_event(event=event, now=now + timedelta(seconds=1))
    authorization = extension.issue_download_authorization(
        order_id="order-1",
        tenant_id="tenant-1",
        user_id="user-1",
        now=now + timedelta(seconds=2),
        ttl=timedelta(minutes=1),
    )
    with pytest.raises(CommercialAccessError, match="principal binding"):
        extension.authorize_download(
            token=authorization.token,
            tenant_id="tenant-1",
            user_id="user-2",
            now=now + timedelta(seconds=3),
        )
    with pytest.raises(CommercialAccessError, match="expired"):
        extension.authorize_download(
            token=authorization.token,
            tenant_id="tenant-1",
            user_id="user-1",
            now=now + timedelta(minutes=2),
        )
