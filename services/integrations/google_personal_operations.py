"""Concrete Google Workspace transports for governed Personal Operations execution."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from services.integrations.personal_operations import (
    ConnectorReceipt,
    PersonalOperationsConnectorAmbiguousError,
    PersonalOperationsConnectorRejectedError,
)


@dataclass(frozen=True, slots=True)
class ResolvedPersonalOAuthCredential:
    """Credential material resolved by the canonical server-side OAuth boundary."""

    authorization_ref: str
    account_id: str
    access_token: str
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.authorization_ref.strip() or not self.account_id.strip() or not self.access_token.strip():
            raise PersonalOperationsConnectorRejectedError("resolved OAuth credential identity is required")
        if not self.scopes or len(self.scopes) != len(set(self.scopes)):
            raise PersonalOperationsConnectorRejectedError("resolved OAuth scopes must be non-empty and unique")
        if any(not scope.strip() for scope in self.scopes):
            raise PersonalOperationsConnectorRejectedError("resolved OAuth scope must be non-blank")


class PersonalOAuthCredentialResolver(Protocol):
    def resolve(self, authorization_ref: str) -> ResolvedPersonalOAuthCredential: ...


@dataclass(frozen=True, slots=True)
class PersonalHttpResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status_code < 100 or self.status_code > 599:
            raise PersonalOperationsConnectorRejectedError("invalid provider HTTP status code")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


class PersonalHttpClient(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> PersonalHttpResponse: ...


class UrllibPersonalHttpClient:
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> PersonalHttpResponse:
        request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return PersonalHttpResponse(
                    status_code=int(response.status),
                    body=response.read(),
                    headers=dict(response.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            return PersonalHttpResponse(
                status_code=int(exc.code),
                body=exc.read(),
                headers=dict(exc.headers.items()) if exc.headers is not None else {},
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PersonalOperationsConnectorAmbiguousError(
                "provider network outcome is ambiguous"
            ) from exc


class _GoogleOAuthConnectorBase:
    def __init__(
        self,
        *,
        authenticated_account: str,
        authorization_ref: str,
        credential_resolver: PersonalOAuthCredentialResolver,
        http: PersonalHttpClient | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not authenticated_account.strip() or not authorization_ref.strip():
            raise PersonalOperationsConnectorRejectedError(
                "authenticated account and OAuth authorization reference are required"
            )
        self.authenticated_account = authenticated_account
        self._authorization_ref = authorization_ref
        self._resolver = credential_resolver
        self._http = http or UrllibPersonalHttpClient()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _credential(self, required_scope: str) -> ResolvedPersonalOAuthCredential:
        credential = self._resolver.resolve(self._authorization_ref)
        if credential.authorization_ref != self._authorization_ref:
            raise PersonalOperationsConnectorRejectedError(
                "resolved OAuth authorization reference mismatch"
            )
        if credential.account_id != self.authenticated_account:
            raise PersonalOperationsConnectorRejectedError(
                "resolved OAuth account does not match authenticated account"
            )
        if required_scope not in credential.scopes:
            raise PersonalOperationsConnectorRejectedError(
                f"resolved OAuth credential is missing required scope: {required_scope}"
            )
        return credential

    def _request_side_effect(
        self,
        *,
        method: str,
        url: str,
        credential: ResolvedPersonalOAuthCredential,
        body: bytes,
    ) -> PersonalHttpResponse:
        try:
            response = self._http.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {credential.access_token}",
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Length": str(len(body)),
                },
                body=body,
            )
        except PersonalOperationsConnectorRejectedError:
            raise
        except PersonalOperationsConnectorAmbiguousError:
            raise
        except Exception as exc:
            raise PersonalOperationsConnectorAmbiguousError(
                "provider request outcome is ambiguous"
            ) from exc
        if response.status_code >= 500:
            raise PersonalOperationsConnectorAmbiguousError(
                f"provider returned ambiguous HTTP {response.status_code}"
            )
        if response.status_code >= 400:
            raise PersonalOperationsConnectorRejectedError(
                f"provider rejected request with HTTP {response.status_code}"
            )
        return response

    def _occurred_at(self) -> datetime:
        occurred_at = self._clock()
        if occurred_at.tzinfo is None:
            raise PersonalOperationsConnectorRejectedError("provider receipt clock must be timezone-aware")
        return occurred_at


class GoogleGmailConnector(_GoogleOAuthConnectorBase):
    provider_name = "gmail-api-v1"
    required_scope = "https://www.googleapis.com/auth/gmail.send"

    def send_email(
        self,
        *,
        target_account: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> ConnectorReceipt:
        if target_account != self.authenticated_account:
            raise PersonalOperationsConnectorRejectedError(
                "Gmail target account does not match authenticated account"
            )
        if not recipient.strip() or not subject.strip() or not body.strip() or not idempotency_key.strip():
            raise PersonalOperationsConnectorRejectedError("Gmail message fields are required")
        credential = self._credential(self.required_scope)
        message = EmailMessage()
        message["From"] = self.authenticated_account
        message["To"] = recipient
        message["Subject"] = subject
        message["Message-ID"] = f"<ilaios-{idempotency_key}@ilaios.local>"
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        request_body = json.dumps({"raw": raw}, separators=(",", ":")).encode("utf-8")
        response = self._request_side_effect(
            method="POST",
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            credential=credential,
            body=request_body,
        )
        payload = _json_object(response)
        message_id = payload.get("id")
        if not isinstance(message_id, str) or not message_id.strip():
            raise PersonalOperationsConnectorAmbiguousError(
                "Gmail accepted send without returning a message ID"
            )
        return ConnectorReceipt(
            self.provider_name,
            message_id,
            self._occurred_at(),
            target_account,
            "success",
        )


class GoogleCalendarConnector(_GoogleOAuthConnectorBase):
    provider_name = "google-calendar-api-v3"
    required_scope = "https://www.googleapis.com/auth/calendar.events"

    def create_event(
        self,
        *,
        target_account: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt:
        self._require_target(target_account)
        event = _payload_object(payload)
        if "start" not in event or "end" not in event:
            raise PersonalOperationsConnectorRejectedError(
                "calendar create payload requires start and end"
            )
        event_id = f"ilaios{sha256(idempotency_key.encode('utf-8')).hexdigest()}"
        supplied_id = event.get("id")
        if supplied_id is not None and supplied_id != event_id:
            raise PersonalOperationsConnectorRejectedError(
                "calendar event ID is reserved for deterministic idempotency"
            )
        event["id"] = event_id
        credential = self._credential(self.required_scope)
        body = json.dumps(event, separators=(",", ":")).encode("utf-8")
        response = self._request_side_effect(
            method="POST",
            url="https://www.googleapis.com/calendar/v3/calendars/primary/events",
            credential=credential,
            body=body,
        )
        return self._calendar_receipt(response, target_account, expected_event_id=event_id)

    def update_event(
        self,
        *,
        target_account: str,
        event_id: str,
        payload: str,
        idempotency_key: str,
    ) -> ConnectorReceipt:
        del idempotency_key
        self._require_target(target_account)
        if not event_id.strip():
            raise PersonalOperationsConnectorRejectedError("calendar event ID is required")
        event = _payload_object(payload)
        credential = self._credential(self.required_scope)
        body = json.dumps(event, separators=(",", ":")).encode("utf-8")
        encoded_event_id = urllib.parse.quote(event_id, safe="")
        response = self._request_side_effect(
            method="PATCH",
            url=(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events/"
                f"{encoded_event_id}"
            ),
            credential=credential,
            body=body,
        )
        return self._calendar_receipt(response, target_account, expected_event_id=event_id)

    def _require_target(self, target_account: str) -> None:
        if target_account != self.authenticated_account:
            raise PersonalOperationsConnectorRejectedError(
                "Calendar target account does not match authenticated account"
            )

    def _calendar_receipt(
        self,
        response: PersonalHttpResponse,
        target_account: str,
        *,
        expected_event_id: str,
    ) -> ConnectorReceipt:
        payload = _json_object(response)
        provider_id = payload.get("id")
        if not isinstance(provider_id, str) or provider_id != expected_event_id:
            raise PersonalOperationsConnectorAmbiguousError(
                "Calendar mutation did not return the expected event ID"
            )
        return ConnectorReceipt(
            self.provider_name,
            provider_id,
            self._occurred_at(),
            target_account,
            "success",
        )


def _payload_object(payload: str) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PersonalOperationsConnectorRejectedError("provider payload must be valid JSON") from exc
    if not isinstance(value, dict):
        raise PersonalOperationsConnectorRejectedError("provider payload must be a JSON object")
    return {str(key): item for key, item in value.items()}


def _json_object(response: PersonalHttpResponse) -> dict[str, object]:
    try:
        value = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PersonalOperationsConnectorAmbiguousError(
            "provider success response is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise PersonalOperationsConnectorAmbiguousError(
            "provider success response must be a JSON object"
        )
    return {str(key): item for key, item in value.items()}
