"""Durable publication side-effect ledger and idempotency authority."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path

from .finished_product import FinishedVideoProduct
from .publishing_package_preparation import PlatformPublishingPackage


class PublicationLedgerError(ValueError):
    """Raised when publication side-effect state cannot be advanced safely."""


class PublicationState(str, Enum):
    PREPARED = "PREPARED"
    SUBMITTING = "SUBMITTING"
    PUBLISHED = "PUBLISHED"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    package_id: str
    platform: str
    account_id: str
    finished_product_id: str
    media_sha256: str
    payload_sha256: str
    state: PublicationState
    external_post_id: str | None
    published_url: str | None
    observed_status: str | None
    created_at: str
    updated_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS publication_side_effects (
 package_id TEXT PRIMARY KEY,
 platform TEXT NOT NULL,
 account_id TEXT NOT NULL,
 finished_product_id TEXT NOT NULL,
 media_sha256 TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 state TEXT NOT NULL,
 external_post_id TEXT,
 published_url TEXT,
 observed_status TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
"""


class PublicationSideEffectLedger:
    """Persist one-way publication intent before any external social side effect."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "publication_side_effects.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def prepare(
        self,
        *,
        package: PlatformPublishingPackage,
        product: FinishedVideoProduct,
    ) -> PublicationRecord:
        _validate_package_product(package, product)
        payload_digest = publication_payload_sha256(package)
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package.package_id,),
            ).fetchone()
            if existing is not None:
                record = _record(existing)
                _same_identity(record, package, product, payload_digest)
                if record.state is PublicationState.PREPARED:
                    return record
                raise PublicationLedgerError(
                    "publication package already has side-effect history; "
                    "reconcile or create a new governed package instead of reposting"
                )
            connection.execute(
                "INSERT INTO publication_side_effects VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    package.package_id,
                    package.platform,
                    package.account_id,
                    product.product_id,
                    product.final_sha256,
                    payload_digest,
                    PublicationState.PREPARED.value,
                    None,
                    None,
                    None,
                    now,
                    now,
                ),
            )
        return self.get(package.package_id)

    def submitting(self, package_id: str) -> PublicationRecord:
        return self._transition(package_id, PublicationState.SUBMITTING)

    def published(
        self,
        *,
        package_id: str,
        external_post_id: str,
        published_url: str | None,
    ) -> PublicationRecord:
        _text("external_post_id", external_post_id)
        if published_url is not None:
            _text("published_url", published_url)
        return self._transition(
            package_id,
            PublicationState.PUBLISHED,
            external_post_id=external_post_id,
            published_url=published_url,
            observed_status="published",
            require=PublicationState.SUBMITTING,
        )

    def ambiguous(self, *, package_id: str, observed_status: str) -> PublicationRecord:
        _text("observed_status", observed_status)
        return self._transition(
            package_id,
            PublicationState.AMBIGUOUS,
            observed_status=observed_status,
            require=PublicationState.SUBMITTING,
        )

    def failed(self, *, package_id: str, observed_status: str) -> PublicationRecord:
        _text("observed_status", observed_status)
        return self._transition(
            package_id,
            PublicationState.FAILED,
            observed_status=observed_status,
            require=PublicationState.SUBMITTING,
        )

    def get(self, package_id: str) -> PublicationRecord:
        _text("package_id", package_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package_id,),
            ).fetchone()
        if row is None:
            raise PublicationLedgerError("publication package does not exist")
        return _record(row)

    def records(self) -> tuple[PublicationRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM publication_side_effects ORDER BY created_at, package_id"
            ).fetchall()
        return tuple(_record(row) for row in rows)

    def _transition(
        self,
        package_id: str,
        state: PublicationState,
        *,
        external_post_id: str | None = None,
        published_url: str | None = None,
        observed_status: str | None = None,
        require: PublicationState | None = None,
    ) -> PublicationRecord:
        _text("package_id", package_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package_id,),
            ).fetchone()
            if row is None:
                raise PublicationLedgerError("publication package does not exist")
            current = _record(row)
            if require is not None and current.state is not require:
                raise PublicationLedgerError(
                    f"publication package must be {require.value} before {state.value}"
                )
            if (
                state is PublicationState.SUBMITTING
                and current.state is not PublicationState.PREPARED
            ):
                raise PublicationLedgerError(
                    "publication may enter SUBMITTING only from PREPARED"
                )
            connection.execute(
                "UPDATE publication_side_effects SET state=?,external_post_id=?,"
                "published_url=?,observed_status=?,updated_at=? WHERE package_id=?",
                (
                    state.value,
                    external_post_id,
                    published_url,
                    observed_status,
                    _now(),
                    package_id,
                ),
            )
        return self.get(package_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection


def publication_payload_sha256(package: PlatformPublishingPackage) -> str:
    material = {
        "package_id": package.package_id,
        "episode_id": package.episode_id,
        "artifact_id": package.artifact_id,
        "acceptance_decision_id": package.acceptance_decision_id,
        "platform": package.platform,
        "account_id": package.account_id,
        "media_sha256_hex": package.media_sha256_hex,
        "media_byte_length": package.media_byte_length,
        "scheduled_at": package.scheduled_at.isoformat(),
        "visibility": package.visibility,
        "title": package.title,
        "description": package.description,
        "tags": list(package.tags),
        "metadata": dict(package.metadata),
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _validate_package_product(
    package: PlatformPublishingPackage,
    product: FinishedVideoProduct,
) -> None:
    if package.media_sha256_hex != product.final_sha256:
        raise PublicationLedgerError(
            "publishing package is not bound to finished product SHA"
        )
    if package.media_byte_length != product.byte_length:
        raise PublicationLedgerError(
            "publishing package byte length differs from finished product"
        )
    media = Path(package.media_path)
    if media.is_symlink() or not media.is_file():
        raise PublicationLedgerError(
            "publishing media must be an existing regular file"
        )
    body = media.read_bytes()
    if (
        len(body) != product.byte_length
        or sha256(body).hexdigest() != product.final_sha256
    ):
        raise PublicationLedgerError(
            "publishing media content differs from finished product evidence"
        )


def _same_identity(
    record: PublicationRecord,
    package: PlatformPublishingPackage,
    product: FinishedVideoProduct,
    payload_digest: str,
) -> None:
    expected = (
        package.platform,
        package.account_id,
        product.product_id,
        product.final_sha256,
        payload_digest,
    )
    observed = (
        record.platform,
        record.account_id,
        record.finished_product_id,
        record.media_sha256,
        record.payload_sha256,
    )
    if observed != expected:
        raise PublicationLedgerError(
            "publication package identity conflicts with durable history"
        )


def _record(row: sqlite3.Row) -> PublicationRecord:
    post_id = row["external_post_id"]
    url = row["published_url"]
    status = row["observed_status"]
    return PublicationRecord(
        package_id=str(row["package_id"]),
        platform=str(row["platform"]),
        account_id=str(row["account_id"]),
        finished_product_id=str(row["finished_product_id"]),
        media_sha256=str(row["media_sha256"]),
        payload_sha256=str(row["payload_sha256"]),
        state=PublicationState(str(row["state"])),
        external_post_id=None if post_id is None else str(post_id),
        published_url=None if url is None else str(url),
        observed_status=None if status is None else str(status),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise PublicationLedgerError(f"{name} must be non-blank normalized text")
