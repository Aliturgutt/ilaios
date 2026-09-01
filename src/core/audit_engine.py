"""Immutable in-memory audit logging for ILAIOS core modules."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType


class AuditValidationError(ValueError):
    """Raised when an audit record contains invalid data."""


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """Immutable representation of a single core audit event."""

    timestamp: datetime
    component: str
    action: str
    status: str
    details: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise AuditValidationError("Audit timestamp must be timezone-aware")

        if self.timestamp.utcoffset() != timezone.utc.utcoffset(self.timestamp):
            raise AuditValidationError("Audit timestamp must use UTC")

        if not self.component.strip():
            raise AuditValidationError("Audit component must not be empty")

        if not self.action.strip():
            raise AuditValidationError("Audit action must not be empty")

        if self.status not in {"success", "failure", "denied"}:
            raise AuditValidationError(
                "Audit status must be 'success', 'failure', or 'denied'"
            )

        object.__setattr__(
            self,
            "details",
            MappingProxyType(dict(self.details)),
        )


class AuditEngine:
    """Append-only in-memory audit store for core execution events."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record(
        self,
        component: str,
        action: str,
        status: str,
        details: Mapping[str, str] | None = None,
        *,
        timestamp: datetime | None = None,
    ) -> AuditRecord:
        """Create and append an immutable audit record."""
        record = AuditRecord(
            timestamp=timestamp or datetime.now(timezone.utc),
            component=component,
            action=action,
            status=status,
            details=details or {},
        )
        self._records.append(record)
        return record

    def get_records(
        self,
        *,
        component: str | None = None,
        action: str | None = None,
        status: str | None = None,
    ) -> tuple[AuditRecord, ...]:
        """Return audit records matching the supplied filters."""
        records = self._records

        if component is not None:
            records = [
                record for record in records if record.component == component
            ]

        if action is not None:
            records = [
                record for record in records if record.action == action
            ]

        if status is not None:
            records = [
                record for record in records if record.status == status
            ]

        return tuple(records)

    def get_latest(self) -> AuditRecord | None:
        """Return the most recently appended audit record."""
        if not self._records:
            return None
        return self._records[-1]

    def count(self) -> int:
        """Return the number of stored audit records."""
        return len(self._records)

    def ingest_event(
        self,
        component: str,
        action: str,
        status: str,
        details: Mapping[str, str] | None = None,
    ) -> AuditRecord:
        """Ingest an audit event and return the created record."""
        return self.record(component, action, status, details)
