"""Durable commercial quote/payment authority and per-job spend reservations.

This store complements managed customer credits.  It protects the seller-side
commercial budget bound to a locked quote so concurrent workers cannot each
consume the same provider ceiling.  SQLite BEGIN IMMEDIATE supplies the local
transaction boundary; production deployments may substitute an equivalent
transactional store behind the same semantics.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .commercial_quote import (
    CommercialDispatchAuthority,
    LockedVideoQuote,
    PaymentAuthorization,
)
from .commercial_types import CommercialAdmissionError, nonnegative_int, require_text
from .managed_credits import ProviderCostQuote


class CommercialReservationState(str, Enum):
    RESERVED = "RESERVED"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"
    COST_POLICY_VIOLATION = "COST_POLICY_VIOLATION"


@dataclass(frozen=True, slots=True)
class CommercialRequestReservation:
    request_id: str
    authority_sha256: str
    quote_id: str
    provider_name: str
    model_id: str
    max_cost_microusd: int
    actual_cost_microusd: int | None
    state: CommercialReservationState


_SCHEMA = """
CREATE TABLE IF NOT EXISTS commercial_quotes (
 quote_id TEXT PRIMARY KEY,
 quote_sha256 TEXT UNIQUE NOT NULL,
 provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL,
 pricing_fingerprint TEXT NOT NULL,
 gross_customer_price_microusd INTEGER NOT NULL CHECK(gross_customer_price_microusd > 0),
 provider_cost_ceiling_microusd INTEGER NOT NULL CHECK(provider_cost_ceiling_microusd > 0),
 hard_min_margin_bps INTEGER NOT NULL,
 created_at_epoch_s INTEGER NOT NULL,
 expires_at_epoch_s INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS commercial_payments (
 payment_authorization_id TEXT PRIMARY KEY,
 quote_id TEXT NOT NULL,
 secured_amount_microusd INTEGER NOT NULL CHECK(secured_amount_microusd > 0),
 secured_at_epoch_s INTEGER NOT NULL,
 status TEXT NOT NULL,
 FOREIGN KEY(quote_id) REFERENCES commercial_quotes(quote_id)
);
CREATE TABLE IF NOT EXISTS commercial_authorities (
 authority_sha256 TEXT PRIMARY KEY,
 quote_id TEXT NOT NULL,
 quote_sha256 TEXT NOT NULL,
 payment_authorization_id TEXT NOT NULL,
 provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL,
 pricing_fingerprint TEXT NOT NULL,
 provider_cost_ceiling_microusd INTEGER NOT NULL CHECK(provider_cost_ceiling_microusd > 0),
 issued_at_epoch_s INTEGER NOT NULL,
 expires_at_epoch_s INTEGER NOT NULL,
 FOREIGN KEY(quote_id) REFERENCES commercial_quotes(quote_id),
 FOREIGN KEY(payment_authorization_id) REFERENCES commercial_payments(payment_authorization_id)
);
CREATE TABLE IF NOT EXISTS commercial_request_reservations (
 request_id TEXT PRIMARY KEY,
 authority_sha256 TEXT NOT NULL,
 quote_id TEXT NOT NULL,
 provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL,
 max_cost_microusd INTEGER NOT NULL CHECK(max_cost_microusd > 0),
 actual_cost_microusd INTEGER,
 state TEXT NOT NULL,
 FOREIGN KEY(authority_sha256) REFERENCES commercial_authorities(authority_sha256),
 FOREIGN KEY(quote_id) REFERENCES commercial_quotes(quote_id)
);
CREATE TABLE IF NOT EXISTS commercial_provider_quarantine (
 provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL,
 reason TEXT NOT NULL,
 PRIMARY KEY(provider_name, model_id)
);
"""


class CommercialAuthorityStore:
    """Persist trusted commercial evidence and atomically reserve quote budget."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "video_commercial_finops.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def record_quote(self, quote: LockedVideoQuote) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM commercial_quotes WHERE quote_id=?", (quote.quote_id,)
            ).fetchone()
            values = self._quote_values(quote)
            if existing is not None:
                if tuple(existing) != values:
                    raise CommercialAdmissionError(
                        "quote_id is already persisted with different economics"
                    )
                return
            connection.execute(
                "INSERT INTO commercial_quotes VALUES (?,?,?,?,?,?,?,?,?,?)", values
            )

    def record_payment(self, payment: PaymentAuthorization) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            quote = connection.execute(
                "SELECT * FROM commercial_quotes WHERE quote_id=?", (payment.quote_id,)
            ).fetchone()
            if quote is None:
                raise CommercialAdmissionError("payment requires a persisted locked quote")
            if payment.status != "SECURED":
                raise CommercialAdmissionError("only secured payment may be persisted")
            if payment.secured_amount_microusd < int(quote["gross_customer_price_microusd"]):
                raise CommercialAdmissionError("secured payment does not cover locked price")
            values = (
                payment.payment_authorization_id,
                payment.quote_id,
                payment.secured_amount_microusd,
                payment.secured_at_epoch_s,
                payment.status,
            )
            existing = connection.execute(
                "SELECT * FROM commercial_payments WHERE payment_authorization_id=?",
                (payment.payment_authorization_id,),
            ).fetchone()
            if existing is not None:
                if tuple(existing) != values:
                    raise CommercialAdmissionError(
                        "payment authorization is already persisted differently"
                    )
                return
            connection.execute(
                "INSERT INTO commercial_payments VALUES (?,?,?,?,?)", values
            )

    def record_authority(self, authority: CommercialDispatchAuthority) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            quote = connection.execute(
                "SELECT * FROM commercial_quotes WHERE quote_id=?", (authority.quote_id,)
            ).fetchone()
            payment = connection.execute(
                "SELECT * FROM commercial_payments WHERE payment_authorization_id=?",
                (authority.payment_authorization_id,),
            ).fetchone()
            self._validate_stored_binding(authority, quote, payment)
            values = self._authority_values(authority)
            existing = connection.execute(
                "SELECT * FROM commercial_authorities WHERE authority_sha256=?",
                (authority.authority_sha256,),
            ).fetchone()
            if existing is not None:
                if tuple(existing) != values:
                    raise CommercialAdmissionError(
                        "commercial authority is already persisted differently"
                    )
                return
            connection.execute(
                "INSERT INTO commercial_authorities VALUES (?,?,?,?,?,?,?,?,?,?)", values
            )

    def verify_authority(
        self, authority: CommercialDispatchAuthority, *, now_epoch_s: int
    ) -> None:
        authority.require_valid(now_epoch_s)
        with self._connect() as connection:
            stored = connection.execute(
                "SELECT * FROM commercial_authorities WHERE authority_sha256=?",
                (authority.authority_sha256,),
            ).fetchone()
            if stored is None or tuple(stored) != self._authority_values(authority):
                raise CommercialAdmissionError(
                    "commercial authority is not durably trusted"
                )
            quote = connection.execute(
                "SELECT * FROM commercial_quotes WHERE quote_id=?", (authority.quote_id,)
            ).fetchone()
            payment = connection.execute(
                "SELECT * FROM commercial_payments WHERE payment_authorization_id=?",
                (authority.payment_authorization_id,),
            ).fetchone()
            self._validate_stored_binding(authority, quote, payment)

    def reserve_request(
        self,
        *,
        authority: CommercialDispatchAuthority,
        request_id: str,
        provider_quote: ProviderCostQuote,
        now_epoch_s: int,
    ) -> CommercialRequestReservation:
        require_text("request_id", request_id)
        authority.require_valid(now_epoch_s)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            stored = connection.execute(
                "SELECT * FROM commercial_authorities WHERE authority_sha256=?",
                (authority.authority_sha256,),
            ).fetchone()
            if stored is None or tuple(stored) != self._authority_values(authority):
                raise CommercialAdmissionError(
                    "commercial authority is not durably trusted"
                )
            quote = connection.execute(
                "SELECT * FROM commercial_quotes WHERE quote_id=?", (authority.quote_id,)
            ).fetchone()
            payment = connection.execute(
                "SELECT * FROM commercial_payments WHERE payment_authorization_id=?",
                (authority.payment_authorization_id,),
            ).fetchone()
            self._validate_stored_binding(authority, quote, payment)
            if quote is None:
                raise CommercialAdmissionError("locked quote disappeared")
            if now_epoch_s >= int(quote["expires_at_epoch_s"]):
                raise CommercialAdmissionError("locked quote expired; requote required")
            if self._is_quarantined(connection, authority.provider_name, authority.model_id):
                raise CommercialAdmissionError(
                    "provider/model is quarantined after a cost anomaly"
                )
            if provider_quote.provider_name != authority.provider_name:
                raise CommercialAdmissionError("provider quote does not match authority")
            if provider_quote.model_id != authority.model_id:
                raise CommercialAdmissionError("provider model does not match authority")
            if provider_quote.max_cost_microusd > authority.provider_cost_ceiling_microusd:
                raise CommercialAdmissionError("request exceeds authority cost ceiling")
            existing = connection.execute(
                "SELECT * FROM commercial_request_reservations WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                raise CommercialAdmissionError(
                    "commercial request_id is single-use; create a governed retry request"
                )
            used = connection.execute(
                "SELECT COALESCE(SUM(CASE WHEN state=? THEN max_cost_microusd "
                "ELSE COALESCE(actual_cost_microusd,0) END),0) AS used "
                "FROM commercial_request_reservations WHERE quote_id=? AND state IN (?,?,?)",
                (
                    CommercialReservationState.RESERVED.value,
                    authority.quote_id,
                    CommercialReservationState.RESERVED.value,
                    CommercialReservationState.SETTLED.value,
                    CommercialReservationState.COST_POLICY_VIOLATION.value,
                ),
            ).fetchone()
            used_microusd = 0 if used is None else int(used["used"])
            ceiling = int(quote["provider_cost_ceiling_microusd"])
            if used_microusd + provider_quote.max_cost_microusd > ceiling:
                raise CommercialAdmissionError(
                    "locked provider budget is exhausted; requote required"
                )
            connection.execute(
                "INSERT INTO commercial_request_reservations "
                "(request_id,authority_sha256,quote_id,provider_name,model_id,"
                "max_cost_microusd,actual_cost_microusd,state) VALUES (?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    authority.authority_sha256,
                    authority.quote_id,
                    authority.provider_name,
                    authority.model_id,
                    provider_quote.max_cost_microusd,
                    None,
                    CommercialReservationState.RESERVED.value,
                ),
            )
        return CommercialRequestReservation(
            request_id=request_id,
            authority_sha256=authority.authority_sha256,
            quote_id=authority.quote_id,
            provider_name=authority.provider_name,
            model_id=authority.model_id,
            max_cost_microusd=provider_quote.max_cost_microusd,
            actual_cost_microusd=None,
            state=CommercialReservationState.RESERVED,
        )

    def release_request(self, request_id: str) -> None:
        require_text("request_id", request_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM commercial_request_reservations WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise CommercialAdmissionError("commercial reservation does not exist")
            if row["state"] == CommercialReservationState.RELEASED.value:
                return
            if row["state"] != CommercialReservationState.RESERVED.value:
                raise CommercialAdmissionError(
                    "only an unspent commercial reservation may be released"
                )
            connection.execute(
                "UPDATE commercial_request_reservations SET state=?,actual_cost_microusd=0 "
                "WHERE request_id=?",
                (CommercialReservationState.RELEASED.value, request_id),
            )

    def settle_request(self, *, request_id: str, actual_cost_microusd: int) -> bool:
        require_text("request_id", request_id)
        nonnegative_int("actual_cost_microusd", actual_cost_microusd)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM commercial_request_reservations WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise CommercialAdmissionError("commercial reservation does not exist")
            if row["state"] == CommercialReservationState.SETTLED.value:
                if int(row["actual_cost_microusd"]) != actual_cost_microusd:
                    raise CommercialAdmissionError("reservation is already settled differently")
                return False
            if row["state"] not in {
                CommercialReservationState.RESERVED.value,
                CommercialReservationState.COST_POLICY_VIOLATION.value,
            }:
                raise CommercialAdmissionError("commercial reservation cannot settle")
            violated = actual_cost_microusd > int(row["max_cost_microusd"])
            state = (
                CommercialReservationState.COST_POLICY_VIOLATION
                if violated
                else CommercialReservationState.SETTLED
            )
            connection.execute(
                "UPDATE commercial_request_reservations SET state=?,actual_cost_microusd=? "
                "WHERE request_id=?",
                (state.value, actual_cost_microusd, request_id),
            )
            if violated:
                reason = "actual provider cost exceeded commercial reservation"
                connection.execute(
                    "INSERT INTO commercial_provider_quarantine VALUES (?,?,?) "
                    "ON CONFLICT(provider_name,model_id) DO UPDATE SET reason=excluded.reason",
                    (row["provider_name"], row["model_id"], reason),
                )
            return violated

    def is_provider_quarantined(self, *, provider_name: str, model_id: str) -> bool:
        require_text("provider_name", provider_name)
        require_text("model_id", model_id)
        with self._connect() as connection:
            return self._is_quarantined(connection, provider_name, model_id)

    @staticmethod
    def _is_quarantined(
        connection: sqlite3.Connection, provider_name: str, model_id: str
    ) -> bool:
        return connection.execute(
            "SELECT 1 FROM commercial_provider_quarantine WHERE provider_name=? AND model_id=?",
            (provider_name, model_id),
        ).fetchone() is not None

    @staticmethod
    def _quote_values(quote: LockedVideoQuote) -> tuple[object, ...]:
        return (
            quote.quote_id,
            quote.quote_sha256,
            quote.provider_name,
            quote.model_id,
            quote.pricing_fingerprint,
            quote.gross_customer_price_microusd,
            quote.provider_cost_ceiling_microusd,
            quote.hard_min_margin_bps,
            quote.created_at_epoch_s,
            quote.expires_at_epoch_s,
        )

    @staticmethod
    def _authority_values(authority: CommercialDispatchAuthority) -> tuple[object, ...]:
        return (
            authority.authority_sha256,
            authority.quote_id,
            authority.quote_sha256,
            authority.payment_authorization_id,
            authority.provider_name,
            authority.model_id,
            authority.pricing_fingerprint,
            authority.provider_cost_ceiling_microusd,
            authority.issued_at_epoch_s,
            authority.expires_at_epoch_s,
        )

    @staticmethod
    def _validate_stored_binding(
        authority: CommercialDispatchAuthority,
        quote: sqlite3.Row | None,
        payment: sqlite3.Row | None,
    ) -> None:
        if quote is None:
            raise CommercialAdmissionError("authority requires a persisted locked quote")
        if payment is None:
            raise CommercialAdmissionError("authority requires persisted secured payment")
        if authority.quote_sha256 != quote["quote_sha256"]:
            raise CommercialAdmissionError("authority quote hash is not trusted")
        if authority.provider_name != quote["provider_name"]:
            raise CommercialAdmissionError("authority provider differs from locked quote")
        if authority.model_id != quote["model_id"]:
            raise CommercialAdmissionError("authority model differs from locked quote")
        if authority.pricing_fingerprint != quote["pricing_fingerprint"]:
            raise CommercialAdmissionError("authority pricing differs from locked quote")
        if authority.provider_cost_ceiling_microusd > int(
            quote["provider_cost_ceiling_microusd"]
        ):
            raise CommercialAdmissionError("authority exceeds locked provider budget")
        if authority.expires_at_epoch_s > int(quote["expires_at_epoch_s"]):
            raise CommercialAdmissionError("authority outlives locked quote")
        if payment["quote_id"] != authority.quote_id or payment["status"] != "SECURED":
            raise CommercialAdmissionError("authority payment binding is invalid")
        if int(payment["secured_amount_microusd"]) < int(
            quote["gross_customer_price_microusd"]
        ):
            raise CommercialAdmissionError("persisted payment is underfunded")
