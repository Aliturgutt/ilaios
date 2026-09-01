"""Signed, idempotent OpenRouter video webhook boundary.

Webhook delivery is only a provider completion signal. It cannot mark an ILAIOS
video accepted, publish it, settle credits by itself, or mutate an unknown job.
Polling remains the recovery path when a webhook is lost.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_EVENT_TYPES = frozenset(
    {
        "video.generation.completed",
        "video.generation.failed",
        "video.generation.cancelled",
        "video.generation.expired",
    }
)
_ALLOWED_STATUSES = frozenset({"completed", "failed", "cancelled", "expired"})
_MAX_SIGNATURE_AGE_SECONDS = 300


class OpenRouterWebhookError(ValueError):
    """Raised when webhook authenticity or state binding cannot be proven."""


@dataclass(frozen=True, slots=True)
class OpenRouterVideoWebhookEvent:
    event_type: str
    idempotency_key: str
    provider_job_id: str
    provider_status: str
    created_at: str
    generation_id: str | None
    model_id: str | None
    raw_body_sha256: str


@dataclass(frozen=True, slots=True)
class OpenRouterWebhookRecord:
    request_id: str
    provider_job_id: str
    idempotency_key: str
    event_type: str
    provider_status: str
    raw_body_sha256: str
    recorded_at_epoch_s: float
    duplicate: bool = False


class OpenRouterVideoWebhookVerifier:
    """Verify OpenRouter timestamped HMAC signatures over exact raw bytes."""

    def __init__(
        self,
        signing_secret: str,
        *,
        clock: Callable[[], float] = time.time,
        max_age_seconds: int = _MAX_SIGNATURE_AGE_SECONDS,
    ) -> None:
        _text("signing_secret", signing_secret)
        if max_age_seconds <= 0:
            raise OpenRouterWebhookError("max_age_seconds must be positive")
        self._secret = signing_secret.encode("utf-8")
        self._clock = clock
        self._max_age_seconds = max_age_seconds

    def verify(
        self,
        *,
        raw_body: bytes,
        signature_header: str,
        idempotency_key: str,
    ) -> OpenRouterVideoWebhookEvent:
        if not raw_body:
            raise OpenRouterWebhookError("webhook raw body must not be empty")
        _text("signature_header", signature_header)
        _text("idempotency_key", idempotency_key)
        timestamp, signature = _parse_signature(signature_header)
        age = self._clock() - float(timestamp)
        if abs(age) > self._max_age_seconds:
            raise OpenRouterWebhookError("webhook signature timestamp is stale")
        signed_payload = str(timestamp).encode("ascii") + b"," + raw_body
        expected = hmac.new(self._secret, signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise OpenRouterWebhookError("webhook signature is invalid")
        try:
            decoded = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenRouterWebhookError("webhook body is not valid UTF-8 JSON") from exc
        if not isinstance(decoded, dict):
            raise OpenRouterWebhookError("webhook body must be a JSON object")
        event_type = decoded.get("type")
        created_at = decoded.get("created_at")
        data = decoded.get("data")
        if not isinstance(event_type, str) or event_type not in _ALLOWED_EVENT_TYPES:
            raise OpenRouterWebhookError("unsupported video webhook event type")
        if not isinstance(created_at, str) or not created_at.strip():
            raise OpenRouterWebhookError("webhook created_at must be non-empty")
        if not isinstance(data, Mapping):
            raise OpenRouterWebhookError("webhook data must be an object")
        provider_job_id = _mapping_text(data, "id")
        status = _mapping_text(data, "status").lower()
        if status not in _ALLOWED_STATUSES:
            raise OpenRouterWebhookError("webhook provider status is not terminal")
        expected_suffix = event_type.removeprefix("video.generation.")
        if status != expected_suffix:
            raise OpenRouterWebhookError("webhook event type does not match status")
        return OpenRouterVideoWebhookEvent(
            event_type=event_type,
            idempotency_key=idempotency_key,
            provider_job_id=provider_job_id,
            provider_status=status,
            created_at=created_at,
            generation_id=_optional_mapping_text(data, "generation_id"),
            model_id=_optional_mapping_text(data, "model"),
            raw_body_sha256=hashlib.sha256(raw_body).hexdigest(),
        )


class OpenRouterVideoWebhookStore:
    """Durable known-job binding and webhook idempotency ledger."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "openrouter_video_webhooks.sqlite3"
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS known_video_jobs (
                    provider_job_id TEXT PRIMARY KEY,
                    request_id TEXT UNIQUE NOT NULL,
                    registered_at_epoch_s REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS video_webhook_events (
                    idempotency_key TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    provider_job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    provider_status TEXT NOT NULL,
                    raw_body_sha256 TEXT NOT NULL,
                    recorded_at_epoch_s REAL NOT NULL,
                    FOREIGN KEY (provider_job_id)
                        REFERENCES known_video_jobs (provider_job_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def register_job(
        self,
        *,
        request_id: str,
        provider_job_id: str,
        registered_at_epoch_s: float | None = None,
    ) -> None:
        _text("request_id", request_id)
        _text("provider_job_id", provider_job_id)
        observed = time.time() if registered_at_epoch_s is None else registered_at_epoch_s
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM known_video_jobs WHERE provider_job_id = ?",
                (provider_job_id,),
            ).fetchone()
            if existing is not None:
                row = _row(existing)
                if str(row["request_id"]) != request_id:
                    raise OpenRouterWebhookError(
                        "provider job is already bound to another request"
                    )
                return
            request_row = connection.execute(
                "SELECT provider_job_id FROM known_video_jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if request_row is not None:
                raise OpenRouterWebhookError(
                    "request is already bound to another provider job"
                )
            connection.execute(
                "INSERT INTO known_video_jobs VALUES (?, ?, ?)",
                (provider_job_id, request_id, observed),
            )

    def record(
        self,
        event: OpenRouterVideoWebhookEvent,
        *,
        recorded_at_epoch_s: float | None = None,
    ) -> OpenRouterWebhookRecord:
        observed = time.time() if recorded_at_epoch_s is None else recorded_at_epoch_s
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            known = connection.execute(
                "SELECT request_id FROM known_video_jobs WHERE provider_job_id = ?",
                (event.provider_job_id,),
            ).fetchone()
            if known is None:
                raise OpenRouterWebhookError("webhook references unknown provider job")
            request_id = str(_row(known)["request_id"])
            duplicate = connection.execute(
                "SELECT * FROM video_webhook_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if duplicate is not None:
                record = _record(_row(duplicate), duplicate=True)
                if (
                    record.provider_job_id != event.provider_job_id
                    or record.raw_body_sha256 != event.raw_body_sha256
                ):
                    raise OpenRouterWebhookError(
                        "idempotency key is bound to different webhook material"
                    )
                return record
            connection.execute(
                "INSERT INTO video_webhook_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.idempotency_key,
                    request_id,
                    event.provider_job_id,
                    event.event_type,
                    event.provider_status,
                    event.raw_body_sha256,
                    observed,
                ),
            )
            saved = connection.execute(
                "SELECT * FROM video_webhook_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if saved is None:
                raise OpenRouterWebhookError("webhook event was not persisted")
            return _record(_row(saved), duplicate=False)


def _parse_signature(header: str) -> tuple[int, str]:
    timestamp: int | None = None
    signature: str | None = None
    for part in header.split(","):
        key, separator, value = part.strip().partition("=")
        if not separator:
            continue
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise OpenRouterWebhookError(
                    "webhook signature timestamp is invalid"
                ) from exc
        elif key == "v1":
            signature = value.lower()
    if timestamp is None or signature is None:
        raise OpenRouterWebhookError("webhook signature requires t and v1")
    if len(signature) != 64 or any(ch not in "0123456789abcdef" for ch in signature):
        raise OpenRouterWebhookError("webhook v1 signature must be SHA-256 hex")
    return timestamp, signature


def _mapping_text(data: Mapping[object, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterWebhookError(f"webhook data {key} must be non-empty string")
    return value


def _optional_mapping_text(data: Mapping[object, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterWebhookError(f"webhook data {key} must be string or null")
    return value


def _record(row: sqlite3.Row, *, duplicate: bool) -> OpenRouterWebhookRecord:
    return OpenRouterWebhookRecord(
        request_id=str(row["request_id"]),
        provider_job_id=str(row["provider_job_id"]),
        idempotency_key=str(row["idempotency_key"]),
        event_type=str(row["event_type"]),
        provider_status=str(row["provider_status"]),
        raw_body_sha256=str(row["raw_body_sha256"]),
        recorded_at_epoch_s=float(row["recorded_at_epoch_s"]),
        duplicate=duplicate,
    )


def _row(value: object) -> sqlite3.Row:
    if not isinstance(value, sqlite3.Row):
        raise OpenRouterWebhookError("SQLite webhook ledger returned invalid row type")
    return value


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise OpenRouterWebhookError(f"{name} must not be blank")
    if value != value.strip():
        raise OpenRouterWebhookError(f"{name} must not contain surrounding whitespace")
