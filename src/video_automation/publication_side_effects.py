"""Durable publication side-effect safety for accepted media packages.

Publication is financially/reputationally consequential external state. A package
identity is therefore single-use: the ledger is written before the POST, timeout
becomes AMBIGUOUS, and no blind repost is allowed. Reconciliation may verify an
already-created platform post but never silently submit it again.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from .publishing_execution import (
    PlatformPublisher,
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from .publishing_package_preparation import PlatformPublishingPackage


class PublicationSideEffectError(RuntimeError):
    """Raised when publication would violate side-effect safety."""


class PublicationSideEffectState(str, Enum):
    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    AMBIGUOUS = "AMBIGUOUS"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class PublicationSideEffectRecord:
    package_id: str
    episode_id: str
    platform: str
    account_id: str
    artifact_sha256: str
    state: PublicationSideEffectState
    provider_name: str | None
    platform_post_id: str | None
    published_url: str | None
    error_code: str | None
    error_message: str | None
    created_at: str
    updated_at: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS publication_side_effects (
 package_id TEXT PRIMARY KEY,
 episode_id TEXT NOT NULL,
 platform TEXT NOT NULL,
 account_id TEXT NOT NULL,
 artifact_sha256 TEXT NOT NULL,
 state TEXT NOT NULL,
 provider_name TEXT,
 platform_post_id TEXT,
 published_url TEXT,
 error_code TEXT,
 error_message TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
"""


class PublicationSideEffectLedger:
    """Persistent single-use ledger keyed by immutable publishing package id."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "publication_side_effects.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection

    def begin(self, package: PlatformPublishingPackage, *, now: datetime) -> PublicationSideEffectRecord:
        timestamp = _utc_iso(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package.package_id,),
            ).fetchone()
            if existing is not None:
                raise PublicationSideEffectError(
                    "publication package already has side-effect history; blind repost blocked"
                )
            connection.execute(
                "INSERT INTO publication_side_effects "
                "(package_id,episode_id,platform,account_id,artifact_sha256,state,"
                "provider_name,platform_post_id,published_url,error_code,error_message,"
                "created_at,updated_at) VALUES (?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,?,?)",
                (
                    package.package_id,
                    package.episode_id,
                    package.platform,
                    package.account_id,
                    package.media_sha256_hex,
                    PublicationSideEffectState.SUBMITTING.value,
                    timestamp,
                    timestamp,
                ),
            )
        return self.get(package.package_id)

    def mark_accepted(
        self,
        package_id: str,
        *,
        provider_name: str,
        platform_post_id: str,
        published_url: str | None,
        now: datetime,
    ) -> PublicationSideEffectRecord:
        return self._transition(
            package_id,
            allowed=(PublicationSideEffectState.SUBMITTING,),
            state=PublicationSideEffectState.ACCEPTED,
            provider_name=_text("provider_name", provider_name),
            platform_post_id=_text("platform_post_id", platform_post_id),
            published_url=_optional_text("published_url", published_url),
            error_code=None,
            error_message=None,
            now=now,
        )

    def mark_ambiguous(
        self,
        package_id: str,
        *,
        provider_name: str,
        error_message: str,
        now: datetime,
    ) -> PublicationSideEffectRecord:
        return self._transition(
            package_id,
            allowed=(PublicationSideEffectState.SUBMITTING,),
            state=PublicationSideEffectState.AMBIGUOUS,
            provider_name=_text("provider_name", provider_name),
            platform_post_id=None,
            published_url=None,
            error_code="ambiguous_timeout",
            error_message=_text("error_message", error_message),
            now=now,
        )

    def mark_failed(
        self,
        package_id: str,
        *,
        provider_name: str,
        error_code: str | None,
        error_message: str,
        now: datetime,
    ) -> PublicationSideEffectRecord:
        return self._transition(
            package_id,
            allowed=(PublicationSideEffectState.SUBMITTING,),
            state=PublicationSideEffectState.FAILED,
            provider_name=_text("provider_name", provider_name),
            platform_post_id=None,
            published_url=None,
            error_code=_optional_text("error_code", error_code),
            error_message=_text("error_message", error_message),
            now=now,
        )

    def verify_existing_publication(
        self,
        package_id: str,
        *,
        platform_post_id: str,
        published_url: str | None,
        now: datetime,
    ) -> PublicationSideEffectRecord:
        current = self.get(package_id)
        if current.state not in (
            PublicationSideEffectState.ACCEPTED,
            PublicationSideEffectState.AMBIGUOUS,
        ):
            raise PublicationSideEffectError(
                "only ACCEPTED or AMBIGUOUS publication may be reconciled as VERIFIED"
            )
        if (
            current.platform_post_id is not None
            and current.platform_post_id != platform_post_id
        ):
            raise PublicationSideEffectError(
                "reconciliation platform_post_id conflicts with recorded publication"
            )
        return self._transition(
            package_id,
            allowed=(
                PublicationSideEffectState.ACCEPTED,
                PublicationSideEffectState.AMBIGUOUS,
            ),
            state=PublicationSideEffectState.VERIFIED,
            provider_name=current.provider_name,
            platform_post_id=_text("platform_post_id", platform_post_id),
            published_url=_optional_text("published_url", published_url),
            error_code=None,
            error_message=None,
            now=now,
        )

    def get(self, package_id: str) -> PublicationSideEffectRecord:
        package_id = _text("package_id", package_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package_id,),
            ).fetchone()
        if row is None:
            raise PublicationSideEffectError("publication side-effect record does not exist")
        return _record(row)

    def _transition(
        self,
        package_id: str,
        *,
        allowed: tuple[PublicationSideEffectState, ...],
        state: PublicationSideEffectState,
        provider_name: str | None,
        platform_post_id: str | None,
        published_url: str | None,
        error_code: str | None,
        error_message: str | None,
        now: datetime,
    ) -> PublicationSideEffectRecord:
        package_id = _text("package_id", package_id)
        timestamp = _utc_iso(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM publication_side_effects WHERE package_id=?",
                (package_id,),
            ).fetchone()
            if row is None:
                raise PublicationSideEffectError("publication side-effect record does not exist")
            current = PublicationSideEffectState(str(row["state"]))
            if current not in allowed:
                raise PublicationSideEffectError(
                    f"invalid publication side-effect transition: {current.value}->{state.value}"
                )
            connection.execute(
                "UPDATE publication_side_effects SET state=?,provider_name=?,"
                "platform_post_id=?,published_url=?,error_code=?,error_message=?,updated_at=? "
                "WHERE package_id=?",
                (
                    state.value,
                    provider_name,
                    platform_post_id,
                    published_url,
                    error_code,
                    error_message,
                    timestamp,
                    package_id,
                ),
            )
        return self.get(package_id)


class SafePlatformPublicationCoordinator:
    """Wrap one explicit publisher with durable no-blind-repost semantics."""

    def __init__(self, ledger: PublicationSideEffectLedger) -> None:
        self._ledger = ledger

    def publish(
        self,
        *,
        package: PlatformPublishingPackage,
        publisher: PlatformPublisher,
        now: datetime,
    ) -> PlatformPublishingObservation:
        if publisher.platform.strip().lower() != package.platform:
            raise PublicationSideEffectError("publisher platform does not match package")
        self._ledger.begin(package, now=now)
        try:
            observation = publisher.publish(package)
        except TimeoutError as exc:
            self._ledger.mark_ambiguous(
                package.package_id,
                provider_name=publisher.publisher_id,
                error_message=str(exc) or "publication request timed out",
                now=now,
            )
            raise PublicationSideEffectError(
                "publication outcome is ambiguous; reconcile before any new publish"
            ) from exc
        except Exception as exc:
            self._ledger.mark_failed(
                package.package_id,
                provider_name=publisher.publisher_id,
                error_code=type(exc).__name__,
                error_message=str(exc) or type(exc).__name__,
                now=now,
            )
            raise
        _validate_observation(package, observation)
        if observation.status is PublishingExecutionStatus.SUCCEEDED:
            assert observation.platform_post_id is not None
            self._ledger.mark_accepted(
                package.package_id,
                provider_name=observation.provider_name,
                platform_post_id=observation.platform_post_id,
                published_url=observation.published_url,
                now=now,
            )
        else:
            assert observation.error_message is not None
            self._ledger.mark_failed(
                package.package_id,
                provider_name=observation.provider_name,
                error_code=observation.error_code,
                error_message=observation.error_message,
                now=now,
            )
        return observation


def _validate_observation(
    package: PlatformPublishingPackage,
    observation: PlatformPublishingObservation,
) -> None:
    if observation.package_id != package.package_id:
        raise PublicationSideEffectError("publisher observation package_id mismatch")
    if observation.platform != package.platform:
        raise PublicationSideEffectError("publisher observation platform mismatch")
    if observation.account_id != package.account_id:
        raise PublicationSideEffectError("publisher observation account_id mismatch")


def _record(row: sqlite3.Row) -> PublicationSideEffectRecord:
    return PublicationSideEffectRecord(
        package_id=str(row["package_id"]),
        episode_id=str(row["episode_id"]),
        platform=str(row["platform"]),
        account_id=str(row["account_id"]),
        artifact_sha256=str(row["artifact_sha256"]),
        state=PublicationSideEffectState(str(row["state"])),
        provider_name=_object_str(row["provider_name"]),
        platform_post_id=_object_str(row["platform_post_id"]),
        published_url=_object_str(row["published_url"]),
        error_code=_object_str(row["error_code"]),
        error_message=_object_str(row["error_message"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _object_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _text(name: str, value: str) -> str:
    if not value or value != value.strip():
        raise PublicationSideEffectError(f"{name} must be non-blank and trimmed")
    return value


def _optional_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _text(name, value)


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PublicationSideEffectError("publication timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()
