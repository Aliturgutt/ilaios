"""Provider-neutral Personal Operations connector adapters behind the canonical ToolGateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.core.tool_gateway import ToolGateway


class PersonalOperationsConnectorError(RuntimeError):
    """Base error for governed personal-operations connectors."""


class PersonalOperationsConnectorRejectedError(PersonalOperationsConnectorError):
    """Deterministic rejection that proves no provider mutation was attempted."""


class PersonalOperationsConnectorAmbiguousError(PersonalOperationsConnectorError):
    """Provider result is uncertain; blind retry is unsafe."""


@dataclass(frozen=True, slots=True)
class ConnectorReceipt:
    provider: str
    provider_id: str
    occurred_at: datetime
    target_account: str
    outcome: str

    def __post_init__(self) -> None:
        if (
            not self.provider.strip()
            or not self.provider_id.strip()
            or not self.target_account.strip()
        ):
            raise PersonalOperationsConnectorRejectedError(
                "connector receipt identity is required"
            )
        if self.occurred_at.tzinfo is None:
            raise PersonalOperationsConnectorRejectedError(
                "connector receipt timestamp must be timezone-aware"
            )
        if self.outcome != "success":
            raise PersonalOperationsConnectorRejectedError(
                "connector receipt must prove successful execution"
            )


class AccountBoundConnector(Protocol):
    authenticated_account: str


class MailConnector(AccountBoundConnector, Protocol):
    def send_email(
        self,
        *,
        target_account: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


class CalendarConnector(AccountBoundConnector, Protocol):
    def create_event(
        self,
        *,
        target_account: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...

    def update_event(
        self,
        *,
        target_account: str,
        event_id: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


class NotesConnector(AccountBoundConnector, Protocol):
    def create_note(
        self,
        *,
        target_account: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


class ReminderConnector(AccountBoundConnector, Protocol):
    def create_reminder(
        self,
        *,
        target_account: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt: ...


def _require_account(authenticated_account: str, target_account: str) -> None:
    if not authenticated_account.strip():
        raise PersonalOperationsConnectorRejectedError(
            "connector authenticated account is required"
        )
    if authenticated_account != target_account:
        raise PersonalOperationsConnectorRejectedError(
            "connector authenticated account does not match target account"
        )


def register_personal_operations_connectors(
    gateway: ToolGateway,
    *,
    mail: MailConnector | None = None,
    calendar: CalendarConnector | None = None,
    notes: NotesConnector | None = None,
    reminders: ReminderConnector | None = None,
) -> None:
    """Register only explicitly configured account-bound connectors."""
    if mail is not None:
        mail_connector = mail

        def send_email(
            *,
            target_account: str,
            recipient: str,
            subject: str,
            body: str,
            idempotency_key: str,
        ) -> ConnectorReceipt:
            _require_account(mail_connector.authenticated_account, target_account)
            return mail_connector.send_email(
                target_account=target_account,
                recipient=recipient,
                subject=subject,
                body=body,
                idempotency_key=idempotency_key,
            )

        gateway.register_handler("personal_operations.send_email", send_email)

    if calendar is not None:
        calendar_connector = calendar

        def create_calendar_event(
            *,
            target_account: str,
            payload: str,
            idempotency_key: str,
        ) -> ConnectorReceipt:
            _require_account(calendar_connector.authenticated_account, target_account)
            return calendar_connector.create_event(
                target_account=target_account,
                payload=payload,
                idempotency_key=idempotency_key,
            )

        def update_calendar_event(
            *,
            target_account: str,
            event_id: str,
            payload: str,
            idempotency_key: str,
        ) -> ConnectorReceipt:
            _require_account(calendar_connector.authenticated_account, target_account)
            return calendar_connector.update_event(
                target_account=target_account,
                event_id=event_id,
                payload=payload,
                idempotency_key=idempotency_key,
            )

        gateway.register_handler(
            "personal_operations.create_calendar_event",
            create_calendar_event,
        )
        gateway.register_handler(
            "personal_operations.update_calendar_event",
            update_calendar_event,
        )

    if notes is not None:
        notes_connector = notes

        def create_note(
            *,
            target_account: str,
            payload: str,
            idempotency_key: str,
        ) -> ConnectorReceipt:
            _require_account(notes_connector.authenticated_account, target_account)
            return notes_connector.create_note(
                target_account=target_account,
                payload=payload,
                idempotency_key=idempotency_key,
            )

        gateway.register_handler("personal_operations.create_note", create_note)

    if reminders is not None:
        reminders_connector = reminders

        def create_reminder(
            *,
            target_account: str,
            payload: str,
            idempotency_key: str,
        ) -> ConnectorReceipt:
            _require_account(reminders_connector.authenticated_account, target_account)
            return reminders_connector.create_reminder(
                target_account=target_account,
                payload=payload,
                idempotency_key=idempotency_key,
            )

        gateway.register_handler(
            "personal_operations.create_reminder",
            create_reminder,
        )
