"""Provider-neutral Personal Operations connector adapters behind the canonical ToolGateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.core.tool_gateway import ToolGateway


class PersonalOperationsConnectorError(RuntimeError):
    """Raised when an authenticated personal-operations connector cannot execute safely."""


@dataclass(frozen=True, slots=True)
class ConnectorReceipt:
    provider: str
    provider_id: str
    occurred_at: datetime
    target_account: str
    outcome: str

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.provider_id.strip() or not self.target_account.strip():
            raise PersonalOperationsConnectorError("connector receipt identity is required")
        if self.occurred_at.tzinfo is None:
            raise PersonalOperationsConnectorError("connector receipt timestamp must be timezone-aware")
        if self.outcome != "success":
            raise PersonalOperationsConnectorError("connector receipt must prove successful execution")


class MailConnector(Protocol):
    def send_email(
        self,
        *,
        target_account: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


class CalendarConnector(Protocol):
    def create_event(
        self, *, target_account: str, payload: str, idempotency_key: str
    ) -> ConnectorReceipt: ...

    def update_event(
        self,
        *,
        target_account: str,
        event_id: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


class NotesConnector(Protocol):
    def create_note(
        self, *, target_account: str, payload: str, idempotency_key: str
    ) -> ConnectorReceipt: ...


class ReminderConnector(Protocol):
    def create_reminder(
        self, *, target_account: str, payload: str, idempotency_key: str
    ) -> ConnectorReceipt: ...


def register_personal_operations_connectors(
    gateway: ToolGateway,
    *,
    mail: MailConnector | None = None,
    calendar: CalendarConnector | None = None,
    notes: NotesConnector | None = None,
    reminders: ReminderConnector | None = None,
) -> None:
    """Register only explicitly configured authenticated connectors on the canonical gateway."""
    if mail is not None:
        gateway.register_handler("personal_operations.send_email", mail.send_email)
    if calendar is not None:
        gateway.register_handler("personal_operations.create_calendar_event", calendar.create_event)
        gateway.register_handler("personal_operations.update_calendar_event", calendar.update_event)
    if notes is not None:
        gateway.register_handler("personal_operations.create_note", notes.create_note)
    if reminders is not None:
        gateway.register_handler("personal_operations.create_reminder", reminders.create_reminder)
