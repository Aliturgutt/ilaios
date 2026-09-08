"""Tests for concrete Google Personal Operations transports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone

import pytest

from services.integrations.google_personal_operations import (
    GoogleCalendarConnector,
    GoogleGmailConnector,
    PersonalHttpResponse,
    ResolvedPersonalOAuthCredential,
)
from services.integrations.personal_operations import PersonalOperationsConnectorRejectedError


NOW = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)


class _Resolver:
    def __init__(self, credential: ResolvedPersonalOAuthCredential) -> None:
        self.credential = credential
        self.calls = 0

    def resolve(self, authorization_ref: str) -> ResolvedPersonalOAuthCredential:
        self.calls += 1
        assert authorization_ref == self.credential.authorization_ref
        return self.credential


class _Http:
    def __init__(self, responses: list[PersonalHttpResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, Mapping[str, str], bytes | None]] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None = None,
        timeout_seconds: int = 30,
    ) -> PersonalHttpResponse:
        del timeout_seconds
        self.calls.append((method, url, headers, body))
        return self.responses.pop(0)


def _credential(*scopes: str, account: str = "account@example.com") -> ResolvedPersonalOAuthCredential:
    return ResolvedPersonalOAuthCredential(
        "oauth-ref-1",
        account,
        "secret-access-token",
        scopes,
    )


def test_gmail_transport_uses_bound_oauth_account_and_returns_provider_receipt() -> None:
    resolver = _Resolver(_credential("https://www.googleapis.com/auth/gmail.send"))
    http = _Http([PersonalHttpResponse(200, b'{"id":"gmail-message-1"}')])
    connector = GoogleGmailConnector(
        authenticated_account="account@example.com",
        authorization_ref="oauth-ref-1",
        credential_resolver=resolver,
        http=http,
        clock=lambda: NOW,
    )

    receipt = connector.send_email(
        target_account="account@example.com",
        recipient="recipient@example.com",
        subject="Subject",
        body="Body",
        idempotency_key="execution-1",
    )

    assert receipt.provider == "gmail-api-v1"
    assert receipt.provider_id == "gmail-message-1"
    assert receipt.target_account == "account@example.com"
    assert http.calls[0][0] == "POST"
    assert http.calls[0][1] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert http.calls[0][2]["Authorization"] == "Bearer secret-access-token"
    request_payload = json.loads((http.calls[0][3] or b"").decode("utf-8"))
    assert isinstance(request_payload["raw"], str)
    assert "secret-access-token" not in (http.calls[0][3] or b"").decode("utf-8")


def test_calendar_create_uses_deterministic_provider_event_id() -> None:
    resolver = _Resolver(_credential("https://www.googleapis.com/auth/calendar.events"))
    expected_id = "ilaios63093cff69b83efb32db20a75f99361252a6d002049942ac28766a81d244e8c6"
    http = _Http([PersonalHttpResponse(200, json.dumps({"id": expected_id}).encode("utf-8"))])
    connector = GoogleCalendarConnector(
        authenticated_account="account@example.com",
        authorization_ref="oauth-ref-1",
        credential_resolver=resolver,
        http=http,
        clock=lambda: NOW,
    )

    receipt = connector.create_event(
        target_account="account@example.com",
        payload='{"summary":"Meeting","start":{"dateTime":"2026-09-09T10:00:00+03:00"},"end":{"dateTime":"2026-09-09T11:00:00+03:00"}}',
        idempotency_key="execution-1",
    )

    assert receipt.provider_id == expected_id
    assert http.calls[0][0] == "POST"
    request_payload = json.loads((http.calls[0][3] or b"").decode("utf-8"))
    assert request_payload["id"] == expected_id


def test_calendar_update_uses_patch_and_expected_event_identity() -> None:
    resolver = _Resolver(_credential("https://www.googleapis.com/auth/calendar.events"))
    http = _Http([PersonalHttpResponse(200, b'{"id":"event-1"}')])
    connector = GoogleCalendarConnector(
        authenticated_account="account@example.com",
        authorization_ref="oauth-ref-1",
        credential_resolver=resolver,
        http=http,
        clock=lambda: NOW,
    )

    receipt = connector.update_event(
        target_account="account@example.com",
        event_id="event-1",
        payload='{"summary":"Updated"}',
        idempotency_key="execution-2",
    )

    assert receipt.provider_id == "event-1"
    assert http.calls[0][0] == "PATCH"
    assert http.calls[0][1].endswith("/events/event-1")


def test_google_transport_fails_closed_before_http_for_wrong_account_or_scope() -> None:
    wrong_account_http = _Http([])
    wrong_account = GoogleGmailConnector(
        authenticated_account="account@example.com",
        authorization_ref="oauth-ref-1",
        credential_resolver=_Resolver(
            _credential("https://www.googleapis.com/auth/gmail.send", account="other@example.com")
        ),
        http=wrong_account_http,
        clock=lambda: NOW,
    )
    with pytest.raises(PersonalOperationsConnectorRejectedError, match="OAuth account"):
        wrong_account.send_email(
            target_account="account@example.com",
            recipient="recipient@example.com",
            subject="Subject",
            body="Body",
            idempotency_key="execution-1",
        )
    assert wrong_account_http.calls == []

    missing_scope_http = _Http([])
    missing_scope = GoogleCalendarConnector(
        authenticated_account="account@example.com",
        authorization_ref="oauth-ref-1",
        credential_resolver=_Resolver(_credential("openid")),
        http=missing_scope_http,
        clock=lambda: NOW,
    )
    with pytest.raises(PersonalOperationsConnectorRejectedError, match="missing required scope"):
        missing_scope.create_event(
            target_account="account@example.com",
            payload='{"start":{"date":"2026-09-09"},"end":{"date":"2026-09-10"}}',
            idempotency_key="execution-1",
        )
    assert missing_scope_http.calls == []
