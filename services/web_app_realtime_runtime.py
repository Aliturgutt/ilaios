"""Authenticated bounded realtime event projection for Phase 7 generated Web Apps.

This module owns no domain mutation, identity, authorization, routing, policy,
approval, audit, or evidence authority. It projects application events only after
canonical Phase-5 CRUD authorization has admitted the caller for the bound
resource type and project runtime.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from services.identity import Principal
from services.web_app_crud_runtime import CrudOperation, WebAppCrudRuntime, WebAppCrudRuntimeError

RealtimeEventType = Literal["created", "updated", "deleted", "state_changed"]


class WebAppRealtimeRuntimeError(RuntimeError):
    """Typed fail-closed realtime projection failure."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RealtimeEvent:
    sequence: int
    event_id: str
    event_type: RealtimeEventType
    tenant_id: str
    resource_type: str
    resource_id: str
    resource_version: int | None
    occurred_at: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class RealtimeBatch:
    events: tuple[RealtimeEvent, ...]
    latest_sequence: int
    has_more: bool


class WebAppRealtimeRuntime:
    """In-process replayable event journal with authenticated subscriptions.

    The journal is intentionally a projection boundary rather than a source of
    truth. A deployment may expose batches through SSE/WebSocket transport, but
    reconnect cursors and authorization are enforced here independently of the
    transport implementation.
    """

    def __init__(
        self,
        crud: WebAppCrudRuntime,
        *,
        max_history: int = 1000,
        max_batch: int = 100,
    ) -> None:
        if max_history < 1 or max_history > 10_000:
            raise ValueError("max_history outside bounded range")
        if max_batch < 1 or max_batch > 500:
            raise ValueError("max_batch outside bounded range")
        self._crud = crud
        self._max_batch = max_batch
        self._events: deque[RealtimeEvent] = deque(maxlen=max_history)
        self._sequence = 0
        self._lock = threading.Lock()

    def publish(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        event_type: RealtimeEventType,
        payload: dict[str, object],
        now: datetime,
        resource_version: int | None = None,
    ) -> RealtimeEvent:
        """Append one bounded projection event after canonical resource authorization."""
        self._token(resource_type, "resource_type")
        self._token(resource_id, "resource_id")
        if event_type not in ("created", "updated", "deleted", "state_changed"):
            raise WebAppRealtimeRuntimeError("INVALID_EVENT_TYPE", "unsupported realtime event")
        if resource_version is not None and resource_version < 1:
            raise WebAppRealtimeRuntimeError(
                "INVALID_RESOURCE_VERSION", "resource_version must be positive"
            )
        self._payload(payload)
        self._authorize_publish(principal, resource_type, event_type, now)
        authoritative_version = self._authoritative_projection_version(
            principal=principal,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=event_type,
        )
        if resource_version is not None and resource_version != authoritative_version:
            raise WebAppRealtimeRuntimeError(
                "RESOURCE_VERSION_MISMATCH",
                "realtime projection version does not match authoritative resource",
                409,
            )
        occurred_at = self._utc(now)
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
            event = RealtimeEvent(
                sequence=sequence,
                event_id=self._event_id(
                    sequence,
                    principal.tenant_id,
                    resource_type,
                    resource_id,
                    event_type,
                    occurred_at,
                ),
                event_type=event_type,
                tenant_id=principal.tenant_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_version=authoritative_version,
                occurred_at=occurred_at,
                payload=dict(payload),
            )
            self._events.append(event)
            return event

    def subscribe(
        self,
        *,
        principal: Principal,
        resource_type: str,
        now: datetime,
        after_sequence: int = 0,
        resource_id: str | None = None,
        limit: int | None = None,
    ) -> RealtimeBatch:
        """Return a replay batch suitable for SSE/WebSocket reconnect semantics."""
        self._token(resource_type, "resource_type")
        if resource_id is not None:
            self._token(resource_id, "resource_id")
        if after_sequence < 0:
            raise WebAppRealtimeRuntimeError("INVALID_CURSOR", "cursor cannot be negative")
        batch_limit = self._max_batch if limit is None else limit
        if batch_limit < 1 or batch_limit > self._max_batch:
            raise WebAppRealtimeRuntimeError("INVALID_LIMIT", "limit outside bounded range")
        self._authorize_subscription(principal, resource_type, now)

        with self._lock:
            snapshot = tuple(self._events)

        scoped = tuple(
            event
            for event in snapshot
            if event.tenant_id == principal.tenant_id
            and event.resource_type == resource_type
            and (resource_id is None or event.resource_id == resource_id)
        )
        if scoped and after_sequence < scoped[0].sequence - 1:
            raise WebAppRealtimeRuntimeError(
                "STALE_CURSOR",
                "realtime cursor predates retained history; full refresh required",
                409,
            )
        matching = tuple(event for event in scoped if event.sequence > after_sequence)
        latest_sequence = scoped[-1].sequence if scoped else after_sequence
        return RealtimeBatch(
            events=matching[:batch_limit],
            latest_sequence=latest_sequence,
            has_more=len(matching) > batch_limit,
        )

    def _authorize_publish(
        self,
        principal: Principal,
        resource_type: str,
        event_type: RealtimeEventType,
        now: datetime,
    ) -> None:
        operations: dict[RealtimeEventType, CrudOperation] = {
            "created": "create",
            "updated": "update",
            "deleted": "delete",
            "state_changed": "update",
        }
        self._crud._authorize(principal, resource_type, operations[event_type], now)

    def _authoritative_projection_version(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        event_type: RealtimeEventType,
    ) -> int:
        """Bind a projection to canonical CRUD state, including post-delete tombstones."""
        deleted_clause = "IS NOT NULL" if event_type == "deleted" else "IS NULL"
        row = self._crud._db.execute(
            f"""SELECT version FROM web_app_resources
                WHERE tenant_id=? AND project_id=? AND resource_type=? AND resource_id=?
                  AND deleted_at {deleted_clause}""",
            (
                principal.tenant_id,
                self._crud._contract.project_id,
                resource_type,
                resource_id,
            ),
        ).fetchone()
        if row is None:
            raise WebAppCrudRuntimeError("NOT_FOUND", "resource not found", 404)
        return int(row["version"])

    def _authorize_subscription(
        self, principal: Principal, resource_type: str, now: datetime
    ) -> None:
        self._crud.list(
            principal=principal,
            resource_type=resource_type,
            now=now,
            offset=0,
            limit=1,
            sort_field="resource_id",
        )

    @staticmethod
    def _event_id(
        sequence: int,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        event_type: RealtimeEventType,
        occurred_at: str,
    ) -> str:
        raw = "|".join(
            (str(sequence), tenant_id, resource_type, resource_id, event_type, occurred_at)
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _token(value: str, label: str) -> None:
        if not value or len(value) > 120 or not all(
            character.isalnum() or character in "-_.:" for character in value
        ):
            raise WebAppRealtimeRuntimeError("INVALID_TOKEN", f"invalid {label}")

    @staticmethod
    def _payload(payload: dict[str, object]) -> None:
        try:
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise WebAppRealtimeRuntimeError(
                "INVALID_PAYLOAD", "payload must be JSON serializable"
            ) from exc
        if len(encoded) > 64 * 1024:
            raise WebAppRealtimeRuntimeError("PAYLOAD_TOO_LARGE", "payload exceeds 64 KiB")

    @staticmethod
    def _utc(value: datetime) -> str:
        if value.tzinfo is None:
            raise WebAppRealtimeRuntimeError("INVALID_TIME", "timestamp must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()


__all__ = [
    "RealtimeBatch",
    "RealtimeEvent",
    "RealtimeEventType",
    "WebAppRealtimeRuntime",
    "WebAppRealtimeRuntimeError",
]
