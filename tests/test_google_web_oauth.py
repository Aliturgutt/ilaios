from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from services.central_identity import IdentityProvider
from services.control_plane.migrations import migrate_database
from services.email_auth import InMemoryEmailChallengeStore, SQLiteEmailChallengeStore
from services.google_oidc import (
    GOOGLE_ISSUER,
    GoogleOIDCConfigurationError,
    GoogleOIDCEnvironment,
)
from services.google_web_oauth import (
    GoogleWebOAuthCredentials,
    GoogleWebOAuthError,
    GoogleWebOAuthIDTokenVerificationError,
    GoogleWebOAuthReplayStore,
    GoogleWebOAuthService,
    GoogleWebOAuthStateError,
    GoogleWebOAuthTokenExchangeError,
    IdentityChallengeGoogleWebOAuthReplayStore,
)
from services.identity import IdentityKind, VerifiedOIDCClaims

_NOW = datetime(2026, 8, 28, 19, 30, tzinfo=timezone.utc)
_REDIRECT = "https://app.ilaios.com/auth/google/callback"
_CLIENT_SECRET = "server-only-client-secret"
_STATE_SECRET = "state-secret-material-that-is-distinct-and-long-enough"


def _oidc(*, redirects: str = _REDIRECT) -> GoogleOIDCEnvironment:
    return GoogleOIDCEnvironment.from_environment(
        {
            "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID": "prod.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID": "dev.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID": "desktop.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS": redirects,
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


def _credentials() -> GoogleWebOAuthCredentials:
    return GoogleWebOAuthCredentials(
        client_secret=_CLIENT_SECRET,
        state_secret=_STATE_SECRET,
    )


def _memory_replay_store() -> GoogleWebOAuthReplayStore:
    return IdentityChallengeGoogleWebOAuthReplayStore(InMemoryEmailChallengeStore())


def _service(
    *,
    replay_store: GoogleWebOAuthReplayStore | None = None,
    session: _Session | None = None,
    verifier: _Verifier | None = None,
    oidc: GoogleOIDCEnvironment | None = None,
) -> tuple[GoogleWebOAuthService, _Session, list[tuple[str, str]]]:
    http = session or _Session()
    captured: list[tuple[str, str]] = []

    def factory(client_id: str, nonce: str) -> _Verifier:
        captured.append((client_id, nonce))
        return verifier or _Verifier(client_id=client_id)

    service = GoogleWebOAuthService(
        oidc=oidc or _oidc(),
        credentials=_credentials(),
        replay_store=replay_store or _memory_replay_store(),
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
    assert _CLIENT_SECRET not in start.authorization_url
    assert _STATE_SECRET not in start.authorization_url


def test_start_rejects_non_allowlisted_redirect() -> None:
    service, _, _ = _service()

    with pytest.raises(GoogleOIDCConfigurationError, match="not allowlisted"):
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
    assert data["client_secret"] == _CLIENT_SECRET
    assert data["code"] == "authorization-code"
    assert data["redirect_uri"] == _REDIRECT
    assert isinstance(data["code_verifier"], str)
    assert 43 <= len(data["code_verifier"]) <= 128
    assert len(captured) == 1
    assert captured[0][0] == "prod.apps.googleusercontent.com"
    assert len(captured[0][1]) >= 32


def test_state_is_single_use_and_replay_fails_before_second_provider_call() -> None:
    service, http, _ = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    service.complete(state=start.state, code="authorization-code", now=_NOW)
    with pytest.raises(GoogleWebOAuthStateError, match="replayed"):
        service.complete(state=start.state, code="authorization-code", now=_NOW)

    assert len(http.calls) == 1


def test_expired_state_fails_closed_without_provider_call() -> None:
    service, http, _ = _service()
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    with pytest.raises(GoogleWebOAuthStateError, match="expired"):
        service.complete(
            state=start.state,
            code="authorization-code",
            now=_NOW + timedelta(minutes=6),
        )

    assert http.calls == []


def test_tampered_redirect_binding_cannot_select_another_allowlisted_redirect() -> None:
    second_redirect = "https://ilaios.com/auth/google/callback"
    oidc = _oidc(redirects=f"{_REDIRECT},{second_redirect}")
    service, http, _ = _service(oidc=oidc)
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)
    parts = start.state.split(".")
    tampered = f"{parts[0]}.1.{parts[2]}"

    with pytest.raises(GoogleWebOAuthStateError, match="invalid"):
        service.complete(state=tampered, code="authorization-code", now=_NOW)

    identity = service.complete(state=start.state, code="authorization-code", now=_NOW)
    assert identity.subject == "google-sub-123"
    assert len(http.calls) == 1
    data = http.calls[0]["data"]
    assert isinstance(data, dict)
    assert data["redirect_uri"] == _REDIRECT


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
        with pytest.raises(GoogleWebOAuthIDTokenVerificationError):
            service.complete(state=start.state, code="authorization-code", now=_NOW)


def test_complete_classifies_missing_id_token_as_token_exchange_failure() -> None:
    service, _, _ = _service(session=_Session(payload={}))
    start = service.start(redirect_uri=_REDIRECT, now=_NOW)

    with pytest.raises(GoogleWebOAuthTokenExchangeError):
        service.complete(state=start.state, code="authorization-code", now=_NOW)


def test_credentials_require_distinct_server_secrets() -> None:
    with pytest.raises(GoogleWebOAuthError, match="client secret"):
        GoogleWebOAuthCredentials.from_environment({})

    env = {
        "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_SECRET": "same-secret-material-that-is-long-enough",
        "ILAIOS_GOOGLE_WEB_OAUTH_STATE_SECRET": "same-secret-material-that-is-long-enough",
    }
    with pytest.raises(GoogleWebOAuthError, match="must be distinct"):
        GoogleWebOAuthCredentials.from_environment(env)


def _sqlite_replay_store(database: Path) -> GoogleWebOAuthReplayStore:
    return IdentityChallengeGoogleWebOAuthReplayStore(
        SQLiteEmailChallengeStore(database)
    )


def test_sqlite_replay_marker_survives_restart_and_stores_no_raw_state(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.sqlite3"
    migrate_database(database)
    first_http = _Session()
    first, _, _ = _service(
        replay_store=_sqlite_replay_store(database),
        session=first_http,
    )
    start = first.start(redirect_uri=_REDIRECT, now=_NOW)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT challenge_id, email, secret_digest, consumed_at "
            "FROM identity_email_challenges"
        ).fetchone()
    assert row is not None
    assert str(row[0]).startswith("goa_")
    assert row[1] == "google-web-oauth@internal.invalid"
    assert len(str(row[2])) == 64
    assert start.state not in tuple(str(value) for value in row if value is not None)
    assert row[3] is None

    restarted_http = _Session()
    restarted, _, _ = _service(
        replay_store=_sqlite_replay_store(database),
        session=restarted_http,
    )
    identity = restarted.complete(
        state=start.state,
        code="authorization-code",
        now=_NOW + timedelta(seconds=30),
    )
    assert identity.subject == "google-sub-123"
    assert len(restarted_http.calls) == 1

    second_restart, second_http, _ = _service(
        replay_store=_sqlite_replay_store(database)
    )
    with pytest.raises(GoogleWebOAuthStateError, match="replayed"):
        second_restart.complete(
            state=start.state,
            code="authorization-code",
            now=_NOW + timedelta(seconds=40),
        )
    assert second_http.calls == []
