from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from services.central_identity import IdentityProvider
from services.google_oidc import GOOGLE_ISSUER, GoogleOIDCEnvironment
from services.google_web_oauth import (
    GoogleWebOAuthCredentials,
    GoogleWebOAuthError,
    GoogleWebOAuthService,
    InMemoryGoogleWebOAuthFlowStore,
)
from services.identity import IdentityKind, VerifiedOIDCClaims

_NOW = datetime(2026, 8, 28, 19, 30, tzinfo=timezone.utc)
_REDIRECT = "https://app.ilaios.com/auth/google/callback"


def _oidc() -> GoogleOIDCEnvironment:
    return GoogleOIDCEnvironment.from_environment(
        {
            "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID": "prod.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID": "dev.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID": "desktop.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS": _REDIRECT,
        }
    )


class _Response:
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _Session(requests.Session):
    def __init__(self, payload: object | None = None) -> None:
        super().__init__()
        self.payload = payload if payload is not None else {"id_token": "verified-token"}
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _Response:  # type: ignore[override]
        self.calls.append({"url": url, **kwargs})
        return _Response(self.payload)


class _Verifier:
    def __init__(
        self,
        *,
        client_id: str,
        issuer: str = GOOGLE_ISSUER,
        issued_at: datetime = _NOW - timedelta(minutes=1),
        expires_at: datetime = _NOW + timedelta(minutes=30),
    ) -> None:
        self._client_id = client_id
        self._issuer = issuer
        self._issued_at = issued_at
        self._expires_at = expires_at
        self.tokens: list[str] = []

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        self.tokens.append(encoded_token)
        return VerifiedOIDCClaims(
            issuer=self._issuer,
            audience=self._client_id,
            subject="google-sub-123",
            tenant_id="provider-derived-not-canonical",
            expires_at=self._expires_at,
            issued_at=self._issued_at,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset({("verified_email", "User@Example.com")}),
            authentication_methods=frozenset({"pwd"}),
        )


def _service(
    *,
    session: _Session | None = None,
    verifier: _Verifier | None = None,
) -> tuple[GoogleWebOAuthService, _Session, list[tuple[str, str]]]:
    http = session or _Session()
    captured: list[tuple[str, str]] = []

    def factory(client_id: str, nonce: str) -> _Verifier:
        captured.append((client_id, nonce))
        return verifier or _Verifier(client_id=client_id)

    service = GoogleWebOAuthService(
        oidc=_oidc(),
        credentials=GoogleWebOAuthCredentials(client_secret="server-only-secret"),
        flows=InMemoryGoogleWebOAuthFlowStore(),
        request_session=http,
        verifier_factory=factory,
    )
    return service, http, captured


def test_start_uses_authorization_code_pkce_state_nonce_and_exact_redirect() -> None:
    service, _, _ = _service()

    start = service.start(redirect_uri=_REDIRECT, now=_NOW)
    parsed = urlparse(start.authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["prod.apps.googleusercontent.com"]
    assert query["redirect_uri"] == [_REDIRECT]
    assert query["state"] == [start.state]
    assert len(query["nonce"][0]) >= 32
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) >= 43
    assert start.expires_at == _NOW + timedelta(minutes=5)


def test_start_rejects_non_allowlisted_redirect() -> None:
    service, _, _ = _service()

    with pytest.raises(Exception, match="not allowlisted"):
        service.start(
            redirect_uri="https://attacker.example/auth/google/callback", now=_NOW
        )


def test_complete_exchanges_code_server_side_and_returns_canonical_external_identity() -> None:
    service, http, captured = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    identity = service.complete(state=start.state, code="authorization-code", now=_NOW)

    assert identity.provider is IdentityProvider.GOOGLE
    assert identity.subject == "google-sub-123"
    assert identity.email == "user@example.com"
    assert identity.key() == (IdentityProvider.GOOGLE, "", "google-sub-123")
    assert len(http.calls) == 1
    data = http.calls[0]["data"]
    assert isinstance(data, dict)
    assert data["grant_type"] == "authorization_code"
    assert data["client_id"] == "prod.apps.googleusercontent.com"
    assert data["client_secret"] == "server-only-secret"
    assert data["code"] == "authorization-code"
    assert data["redirect_uri"] == _REDIRECT
    assert isinstance(data["code_verifier"], str)
    assert len(data["code_verifier"]) >= 64
    assert len(captured) == 1
    assert captured[0][0] == "prod.apps.googleusercontent.com"
    assert len(captured[0][1]) >= 32


def test_state_is_single_use_and_replay_fails_before_second_provider_call() -> None:
    service, http, _ = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    service.complete(state=start.state, code="authorization-code", now=_NOW)
    with pytest.raises(GoogleWebOAuthError, match="replayed"):
        service.complete(state=start.state, code="authorization-code", now=_NOW)

    assert len(http.calls) == 1


def test_expired_state_fails_closed_without_provider_call() -> None:
    service, http, _ = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    with pytest.raises(GoogleWebOAuthError, match="expired"):
        service.complete(
            state=start.state,
            code="authorization-code",
            now=_NOW + timedelta(minutes=6),
        )

    assert http.calls == []


def test_verified_claims_reject_wrong_issuer_audience_and_time() -> None:
    cases = (
        _Verifier(client_id="prod.apps.googleusercontent.com", issuer="https://evil.example"),
        _Verifier(client_id="wrong.apps.googleusercontent.com"),
        _Verifier(
            client_id="prod.apps.googleusercontent.com",
            issued_at=_NOW + timedelta(seconds=1),
        ),
        _Verifier(
            client_id="prod.apps.googleusercontent.com",
            expires_at=_NOW,
        ),
    )
    for verifier in cases:
        service, _, _ = _service(verifier=verifier)
        start = service.start(redirect_uri=_REDIRECT, now=_NOW)
        with pytest.raises(GoogleWebOAuthError):
            service.complete(state=start.state, code="authorization-code", now=_NOW)


def test_client_secret_environment_is_required_and_never_embedded_in_start_url() -> None:
    with pytest.raises(GoogleWebOAuthError, match="client secret is required"):
        GoogleWebOAuthCredentials.from_environment({})

    service, _, _ = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)
    assert "server-only-secret" not in start.authorization_url
