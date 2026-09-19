"""Durable cache for private Video Factory reference visual briefs.

The cache prevents repeated multimodal analysis when an admitted execution is
resumed or retried. It is local/private runtime state, not accepted evidence.
Once a request has a brief, its source digest tuple and analyzer identity are
immutable so retries cannot silently change visual conditioning.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_MAX_REFERENCES = 20
_MAX_BRIEF_CHARS = 12_000
_MAX_ANALYZER_ID_CHARS = 256


class ReferenceBriefCacheError(ValueError):
    """Raised when cached reference conditioning is malformed or inconsistent."""


@dataclass(frozen=True, slots=True)
class CachedReferenceBrief:
    request_id: str
    text: str
    reference_sha256s: tuple[str, ...]
    analyzer_id: str
    created_at: datetime


class ReferenceBriefCache:
    """SQLite-backed immutable request-to-reference-brief mapping."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reference_visual_briefs (
                    request_id TEXT PRIMARY KEY,
                    brief_text TEXT NOT NULL,
                    reference_sha256s_json TEXT NOT NULL,
                    analyzer_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, request_id: str) -> CachedReferenceBrief | None:
        _request_id(request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reference_visual_briefs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return _record(row)

    def put(
        self,
        *,
        request_id: str,
        text: str,
        reference_sha256s: tuple[str, ...],
        analyzer_id: str,
    ) -> CachedReferenceBrief:
        _request_id(request_id)
        normalized_text = _brief_text(text)
        normalized_digests = _digests(reference_sha256s)
        normalized_analyzer = _analyzer_id(analyzer_id)
        created_at = datetime.now(timezone.utc)
        serialized_digests = json.dumps(
            normalized_digests,
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM reference_visual_briefs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                record = _record(existing)
                if (
                    record.text != normalized_text
                    or record.reference_sha256s != normalized_digests
                    or record.analyzer_id != normalized_analyzer
                ):
                    raise ReferenceBriefCacheError(
                        "reference visual brief is already frozen for this request"
                    )
                return record
            connection.execute(
                "INSERT INTO reference_visual_briefs "
                "(request_id, brief_text, reference_sha256s_json, analyzer_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    request_id,
                    normalized_text,
                    serialized_digests,
                    normalized_analyzer,
                    created_at.isoformat(),
                ),
            )
        return CachedReferenceBrief(
            request_id=request_id,
            text=normalized_text,
            reference_sha256s=normalized_digests,
            analyzer_id=normalized_analyzer,
            created_at=created_at,
        )


def _record(row: sqlite3.Row) -> CachedReferenceBrief:
    request_id = str(row["request_id"])
    _request_id(request_id)
    text = _brief_text(str(row["brief_text"]))
    analyzer_id = _analyzer_id(str(row["analyzer_id"]))
    try:
        raw_digests = json.loads(str(row["reference_sha256s_json"]))
    except json.JSONDecodeError as error:
        raise ReferenceBriefCacheError(
            "cached reference digest list is invalid JSON"
        ) from error
    if not isinstance(raw_digests, list) or not all(
        isinstance(value, str) for value in raw_digests
    ):
        raise ReferenceBriefCacheError("cached reference digest list is malformed")
    digests = _digests(tuple(raw_digests))
    try:
        created_at = datetime.fromisoformat(str(row["created_at"]))
    except ValueError as error:
        raise ReferenceBriefCacheError("cached reference timestamp is invalid") from error
    if created_at.tzinfo is None:
        raise ReferenceBriefCacheError("cached reference timestamp must be timezone-aware")
    return CachedReferenceBrief(
        request_id=request_id,
        text=text,
        reference_sha256s=digests,
        analyzer_id=analyzer_id,
        created_at=created_at,
    )


def _request_id(value: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 128
        or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for character in value
        )
    ):
        raise ReferenceBriefCacheError("invalid reference brief request id")


def _brief_text(value: str) -> str:
    if not value or value != value.strip() or len(value) > _MAX_BRIEF_CHARS:
        raise ReferenceBriefCacheError("reference visual brief text is invalid")
    return value


def _digests(values: tuple[str, ...]) -> tuple[str, ...]:
    if not values or len(values) > _MAX_REFERENCES:
        raise ReferenceBriefCacheError("reference visual brief digest count is invalid")
    if len(set(values)) != len(values):
        raise ReferenceBriefCacheError("reference visual brief digests must be unique")
    for value in values:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ReferenceBriefCacheError("reference visual brief digest is invalid")
    return values


def _analyzer_id(value: str) -> str:
    if not value or value != value.strip() or len(value) > _MAX_ANALYZER_ID_CHARS:
        raise ReferenceBriefCacheError("reference visual brief analyzer id is invalid")
    return value
