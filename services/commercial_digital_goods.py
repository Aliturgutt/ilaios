"""Digital-goods extension of the canonical commercial access authority.

This module does not collect payments, publish products, own provider credentials, or
create a second commerce authority. It can only be constructed over the existing
``CommercialAccessStore`` backend and persists digital-product/order/delivery state in
the same canonical commercial database transaction boundary.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol

from services.commercial_access import CommercialAccessError
from services.commercial_webhook import VerifiedDigitalPaymentEvent
from services.creative_document_factory import BookExportManifest, BookManifest


_MAX_DOWNLOAD_TTL = timedelta(minutes=15)


class DigitalOrderState(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    REVOKED = "REVOKED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DigitalBookProduct:
    product_id: str
    book_id: str
    book_version: str
    book_content_sha256: str
    export_fingerprint_sha256: str
    price_minor: int
    currency: str
    active: bool


@dataclass(frozen=True, slots=True)
class DigitalBookOrder:
    order_id: str
    provider_order_id: str
    tenant_id: str
    user_id: str
    product_id: str
    price_minor: int
    currency: str
    state: DigitalOrderState
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DownloadAuthorization:
    token: str
    order_id: str
    product_id: str
    expires_at: datetime


class _CommercialAccessBackend(Protocol):
    def _connect(self) -> sqlite3.Connection: ...


_DIGITAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS commercial_digital_products (
 product_id TEXT PRIMARY KEY,
 book_id TEXT NOT NULL,
 book_version TEXT NOT NULL,
 book_content_sha256 TEXT NOT NULL,
 export_fingerprint_sha256 TEXT NOT NULL,
 price_minor INTEGER NOT NULL CHECK (price_minor > 0),
 currency TEXT NOT NULL,
 active INTEGER NOT NULL CHECK (active IN (0, 1)),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commercial_digital_orders (
 order_id TEXT PRIMARY KEY,
 provider_order_id TEXT NOT NULL UNIQUE,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 product_id TEXT NOT NULL,
 price_minor INTEGER NOT NULL CHECK (price_minor > 0),
 currency TEXT NOT NULL,
 state TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(product_id) REFERENCES commercial_digital_products(product_id)
);
CREATE TABLE IF NOT EXISTS commercial_digital_payment_events (
 event_id TEXT PRIMARY KEY,
 provider_order_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 order_snapshot_json TEXT NOT NULL,
 applied_at TEXT NOT NULL,
 FOREIGN KEY(provider_order_id) REFERENCES commercial_digital_orders(provider_order_id)
);
CREATE TABLE IF NOT EXISTS commercial_digital_download_tokens (
 token_sha256 TEXT PRIMARY KEY,
 order_id TEXT NOT NULL,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 product_id TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 revoked INTEGER NOT NULL CHECK (revoked IN (0, 1)),
 created_at TEXT NOT NULL,
 FOREIGN KEY(order_id) REFERENCES commercial_digital_orders(order_id)
);
CREATE INDEX IF NOT EXISTS commercial_digital_orders_principal_idx
 ON commercial_digital_orders(tenant_id, user_id, product_id);
"""


class CommercialDigitalGoodsExtension:
    """Extend canonical commercial access with one-off digital-product state only."""

    def __init__(self, access_store: _CommercialAccessBackend) -> None:
        self._access_store = access_store
        with self._access_store._connect() as connection:
            connection.executescript(_DIGITAL_SCHEMA)

    def register_approved_book_product(
        self,
        *,
        product_id: str,
        book: BookManifest,
        export: BookExportManifest,
        price_minor: int,
        currency: str,
        now: datetime,
    ) -> DigitalBookProduct:
        _require_text("product_id", product_id)
        _require_time("now", now)
        if not book.approved:
            raise CommercialAccessError("unapproved book cannot become a digital product")
        if export.book_id != book.book_id:
            raise CommercialAccessError("book export identity does not match approved book")
        if export.book_content_sha256 != book.content_sha256:
            raise CommercialAccessError("book export content hash does not match approved book")
        if export.build_version != book.build_version:
            raise CommercialAccessError("book export version does not match approved book")
        _require_sha256("pdf_sha256", export.pdf_sha256)
        _require_sha256("epub_sha256", export.epub_sha256)
        _require_sha256("cover_sha256", export.cover_sha256)
        _require_sha256("provenance_sha256", export.provenance_sha256)
        _require_positive_price(price_minor)
        normalized_currency = _normalize_currency(currency)
        fingerprint = _export_fingerprint(export)
        candidate = DigitalBookProduct(
            product_id=product_id,
            book_id=book.book_id,
            book_version=book.build_version,
            book_content_sha256=book.content_sha256,
            export_fingerprint_sha256=fingerprint,
            price_minor=price_minor,
            currency=normalized_currency,
            active=True,
        )
        with self._access_store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM commercial_digital_products WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if existing is not None:
                stored = _product_from_row(existing)
                if stored != candidate:
                    raise CommercialAccessError("product_id conflicts with different digital product")
                return stored
            connection.execute(
                "INSERT INTO commercial_digital_products "
                "(product_id,book_id,book_version,book_content_sha256,export_fingerprint_sha256,"
                "price_minor,currency,active,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    candidate.product_id,
                    candidate.book_id,
                    candidate.book_version,
                    candidate.book_content_sha256,
                    candidate.export_fingerprint_sha256,
                    candidate.price_minor,
                    candidate.currency,
                    1,
                    now.isoformat(),
                ),
            )
        return candidate

    def create_pending_order(
        self,
        *,
        order_id: str,
        provider_order_id: str,
        tenant_id: str,
        user_id: str,
        product_id: str,
        price_minor: int,
        currency: str,
        now: datetime,
    ) -> DigitalBookOrder:
        for name, value in (
            ("order_id", order_id),
            ("provider_order_id", provider_order_id),
            ("tenant_id", tenant_id),
            ("user_id", user_id),
            ("product_id", product_id),
        ):
            _require_text(name, value)
        _require_time("now", now)
        _require_positive_price(price_minor)
        normalized_currency = _normalize_currency(currency)
        with self._access_store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            product_row = connection.execute(
                "SELECT * FROM commercial_digital_products WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if product_row is None:
                raise CommercialAccessError("digital product does not exist")
            product = _product_from_row(product_row)
            if not product.active:
                raise CommercialAccessError("digital product is not active")
            if price_minor != product.price_minor or normalized_currency != product.currency:
                raise CommercialAccessError("client/provider order price does not match server product price")
            existing = connection.execute(
                "SELECT * FROM commercial_digital_orders WHERE order_id = ? OR provider_order_id = ?",
                (order_id, provider_order_id),
            ).fetchone()
            candidate = DigitalBookOrder(
                order_id=order_id,
                provider_order_id=provider_order_id,
                tenant_id=tenant_id,
                user_id=user_id,
                product_id=product_id,
                price_minor=price_minor,
                currency=normalized_currency,
                state=DigitalOrderState.PENDING,
                created_at=now,
                updated_at=now,
            )
            if existing is not None:
                stored = _order_from_row(existing)
                if stored != candidate:
                    raise CommercialAccessError("order identity conflicts with different canonical binding")
                return stored
            connection.execute(
                "INSERT INTO commercial_digital_orders "
                "(order_id,provider_order_id,tenant_id,user_id,product_id,price_minor,currency,state,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    candidate.order_id,
                    candidate.provider_order_id,
                    candidate.tenant_id,
                    candidate.user_id,
                    candidate.product_id,
                    candidate.price_minor,
                    candidate.currency,
                    candidate.state.value,
                    candidate.created_at.isoformat(),
                    candidate.updated_at.isoformat(),
                ),
            )
        return candidate

    def apply_verified_payment_event(
        self,
        *,
        event: VerifiedDigitalPaymentEvent,
        now: datetime,
    ) -> DigitalBookOrder:
        if not isinstance(event, VerifiedDigitalPaymentEvent):
            raise CommercialAccessError("digital payment event must be cryptographically verified")
        _require_time("now", now)
        state_by_event = {
            "payment.succeeded": DigitalOrderState.PAID,
            "payment.failed": DigitalOrderState.FAILED,
            "payment.refunded": DigitalOrderState.REVOKED,
            "payment.chargeback": DigitalOrderState.REVOKED,
            "payment.cancelled": DigitalOrderState.REVOKED,
        }
        target_state = state_by_event.get(event.event_type)
        if target_state is None:
            raise CommercialAccessError("digital payment event type is unsupported")
        with self._access_store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous_event = connection.execute(
                "SELECT * FROM commercial_digital_payment_events WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()
            if previous_event is not None:
                if (
                    str(previous_event["provider_order_id"]) != event.provider_order_id
                    or str(previous_event["event_type"]) != event.event_type
                    or str(previous_event["payload_sha256"]) != event.payload_sha256
                ):
                    raise CommercialAccessError("payment event_id conflicts with different verified content")
                return _order_from_json(str(previous_event["order_snapshot_json"]))
            row = connection.execute(
                "SELECT * FROM commercial_digital_orders WHERE provider_order_id = ?",
                (event.provider_order_id,),
            ).fetchone()
            if row is None:
                raise CommercialAccessError("verified payment references unknown provider order")
            order = _order_from_row(row)
            if event.occurred_at < order.created_at:
                raise CommercialAccessError("verified payment event predates canonical order")
            if order.state is DigitalOrderState.REVOKED and target_state is DigitalOrderState.PAID:
                raise CommercialAccessError("revoked digital order cannot be reactivated by replayed payment")
            updated = DigitalBookOrder(
                order_id=order.order_id,
                provider_order_id=order.provider_order_id,
                tenant_id=order.tenant_id,
                user_id=order.user_id,
                product_id=order.product_id,
                price_minor=order.price_minor,
                currency=order.currency,
                state=target_state,
                created_at=order.created_at,
                updated_at=now,
            )
            snapshot = _order_json(updated)
            connection.execute(
                "UPDATE commercial_digital_orders SET state = ?, updated_at = ? WHERE order_id = ?",
                (updated.state.value, updated.updated_at.isoformat(), updated.order_id),
            )
            connection.execute(
                "INSERT INTO commercial_digital_payment_events "
                "(event_id,provider_order_id,event_type,payload_sha256,order_snapshot_json,applied_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.provider_order_id,
                    event.event_type,
                    event.payload_sha256,
                    snapshot,
                    now.isoformat(),
                ),
            )
            if target_state is DigitalOrderState.REVOKED:
                connection.execute(
                    "UPDATE commercial_digital_download_tokens SET revoked = 1 WHERE order_id = ?",
                    (updated.order_id,),
                )
        return updated

    def issue_download_authorization(
        self,
        *,
        order_id: str,
        tenant_id: str,
        user_id: str,
        now: datetime,
        ttl: timedelta = timedelta(minutes=10),
    ) -> DownloadAuthorization:
        for name, value in (("order_id", order_id), ("tenant_id", tenant_id), ("user_id", user_id)):
            _require_text(name, value)
        _require_time("now", now)
        if ttl <= timedelta(0) or ttl > _MAX_DOWNLOAD_TTL:
            raise CommercialAccessError("download authorization ttl is outside policy")
        with self._access_store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM commercial_digital_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise CommercialAccessError("digital order does not exist")
            order = _order_from_row(row)
            if order.tenant_id != tenant_id or order.user_id != user_id:
                raise CommercialAccessError("digital order principal binding does not match")
            if order.state is not DigitalOrderState.PAID:
                raise CommercialAccessError("only a paid digital order may authorize download")
            token = secrets.token_urlsafe(32)
            token_sha256 = hashlib.sha256(token.encode("utf-8")).hexdigest()
            expires_at = now + ttl
            connection.execute(
                "INSERT INTO commercial_digital_download_tokens "
                "(token_sha256,order_id,tenant_id,user_id,product_id,expires_at,revoked,created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    token_sha256,
                    order.order_id,
                    order.tenant_id,
                    order.user_id,
                    order.product_id,
                    expires_at.isoformat(),
                    0,
                    now.isoformat(),
                ),
            )
        return DownloadAuthorization(token, order.order_id, order.product_id, expires_at)

    def authorize_download(
        self,
        *,
        token: str,
        tenant_id: str,
        user_id: str,
        now: datetime,
    ) -> DigitalBookProduct:
        for name, value in (("token", token), ("tenant_id", tenant_id), ("user_id", user_id)):
            _require_text(name, value)
        _require_time("now", now)
        token_sha256 = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._access_store._connect() as connection:
            token_row = connection.execute(
                "SELECT * FROM commercial_digital_download_tokens WHERE token_sha256 = ?",
                (token_sha256,),
            ).fetchone()
            if token_row is None:
                raise CommercialAccessError("download authorization is invalid")
            if bool(token_row["revoked"]):
                raise CommercialAccessError("download authorization is revoked")
            if str(token_row["tenant_id"]) != tenant_id or str(token_row["user_id"]) != user_id:
                raise CommercialAccessError("download authorization principal binding does not match")
            expires_at = datetime.fromisoformat(str(token_row["expires_at"]))
            if now >= expires_at:
                raise CommercialAccessError("download authorization has expired")
            order_row = connection.execute(
                "SELECT * FROM commercial_digital_orders WHERE order_id = ?",
                (str(token_row["order_id"]),),
            ).fetchone()
            if order_row is None or _order_from_row(order_row).state is not DigitalOrderState.PAID:
                raise CommercialAccessError("download order is not entitled")
            product_row = connection.execute(
                "SELECT * FROM commercial_digital_products WHERE product_id = ?",
                (str(token_row["product_id"]),),
            ).fetchone()
            if product_row is None:
                raise CommercialAccessError("download product does not exist")
            return _product_from_row(product_row)


def _export_fingerprint(export: BookExportManifest) -> str:
    payload = json.dumps(
        {
            "book_id": export.book_id,
            "build_version": export.build_version,
            "book_content_sha256": export.book_content_sha256,
            "pdf_sha256": export.pdf_sha256,
            "epub_sha256": export.epub_sha256,
            "cover_sha256": export.cover_sha256,
            "provenance_sha256": export.provenance_sha256,
            "source_provenance_map": export.source_provenance_map,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _product_from_row(row: sqlite3.Row) -> DigitalBookProduct:
    return DigitalBookProduct(
        product_id=str(row["product_id"]),
        book_id=str(row["book_id"]),
        book_version=str(row["book_version"]),
        book_content_sha256=str(row["book_content_sha256"]),
        export_fingerprint_sha256=str(row["export_fingerprint_sha256"]),
        price_minor=int(row["price_minor"]),
        currency=str(row["currency"]),
        active=bool(row["active"]),
    )


def _order_from_row(row: sqlite3.Row) -> DigitalBookOrder:
    return DigitalBookOrder(
        order_id=str(row["order_id"]),
        provider_order_id=str(row["provider_order_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        product_id=str(row["product_id"]),
        price_minor=int(row["price_minor"]),
        currency=str(row["currency"]),
        state=DigitalOrderState(str(row["state"])),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _order_json(order: DigitalBookOrder) -> str:
    return json.dumps(
        {
            "order_id": order.order_id,
            "provider_order_id": order.provider_order_id,
            "tenant_id": order.tenant_id,
            "user_id": order.user_id,
            "product_id": order.product_id,
            "price_minor": order.price_minor,
            "currency": order.currency,
            "state": order.state.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _order_from_json(payload: str) -> DigitalBookOrder:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise CommercialAccessError("stored digital order snapshot is invalid")
    return DigitalBookOrder(
        order_id=str(data["order_id"]),
        provider_order_id=str(data["provider_order_id"]),
        tenant_id=str(data["tenant_id"]),
        user_id=str(data["user_id"]),
        product_id=str(data["product_id"]),
        price_minor=int(data["price_minor"]),
        currency=str(data["currency"]),
        state=DigitalOrderState(str(data["state"])),
        created_at=datetime.fromisoformat(str(data["created_at"])),
        updated_at=datetime.fromisoformat(str(data["updated_at"])),
    )


def _normalize_currency(value: str) -> str:
    _require_text("currency", value)
    normalized = value.upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise CommercialAccessError("currency must be a three-letter code")
    return normalized


def _require_positive_price(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CommercialAccessError("digital product price must be a positive integer minor-unit amount")


def _require_sha256(name: str, value: str) -> None:
    _require_text(name, value)
    if len(value) != 64:
        raise CommercialAccessError(f"{name} must be a sha256 hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise CommercialAccessError(f"{name} must be a sha256 hex digest") from exc


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError(f"{name} must be non-blank and trimmed")


def _require_time(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CommercialAccessError(f"{name} must be timezone-aware")


__all__ = [
    "CommercialDigitalGoodsExtension",
    "DigitalBookOrder",
    "DigitalBookProduct",
    "DigitalOrderState",
    "DownloadAuthorization",
]
