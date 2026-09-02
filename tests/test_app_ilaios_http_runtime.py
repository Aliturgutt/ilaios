from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest

import apps.web_app_runtime.server as runtime_server
from apps.web_app_runtime.server import (
    AppHTTPServer,
    AppRateLimiter,
    AppRuntime,
    AppRuntimeConfigurationError,
    AppRuntimeEnvironment,
    RuntimeRequest,
)
from services.canonical_browser_session import (
    CanonicalBrowserSessionAuthority,
    CanonicalBrowserSessionError,
)
from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.control_plane.migrations import migrate_database
from services.google_oidc import GoogleDesktopIdentityVerificationError
from services.google_web_canonical_identity import GoogleWebCanonicalIdentityError
from services.google_web_oauth import (
    GoogleWebOAuthExpiredTokenError,
    GoogleWebOAuthIDTokenVerificationError,
    GoogleWebOAuthIssuerAudienceError,
    GoogleWebOAuthIssuedAtFutureError,
    GoogleWebOAuthJwksResolutionError,
    GoogleWebOAuthJWTDecodeError,
    GoogleWebOAuthLifetimeExceededError,
    GoogleWebOAuthMalformedClaimsError,
    GoogleWebOAuthNonceError,
    GoogleWebOAuthService,
    GoogleWebOAuthStart,
    GoogleWebOAuthStateError,
    GoogleWebOAuthTemporalClaimsError,
    GoogleWebOAuthTokenExchangeError,
)
from services.li_founder_operator import LiFounderConfig, LiFounderOperator
from services.web_identity_session_http import WebIdentitySessionBoundary

_NOW = datetime(2026, 8, 29, 14, 0, tzinfo=UTC)
_ORIGIN = "https://app.ilaios.com"
_CALLBACK = "https://app.ilaios.com/auth/google/callback"


class _OAuth:
    def __init__(self, subject: str = "google-subject-123") -> None:
        self.subject = subject
        self.start_redirects: list[str] = []
        self.completions: list[tuple[str, str]] = []

    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
        self.start_redirects.append(redirect_uri)
        return GoogleWebOAuthStart(
            state="goa_test.0.state-value",
            authorization_url=(
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"redirect_uri={redirect_uri}&state=goa_test.0.state-value"
            ),
            expires_at=now + timedelta(minutes=5),
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        self.completions.append((state, code))
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject=self.subject,
            email="owner@example.com",
            email_verified=True,
        )


class _FailingOAuth(_OAuth):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._error = error

    def complete(
        self,
        *,
        state: str,
        code: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        raise self._error


def _environment(database: Path) -> AppRuntimeEnvironment:
    migrate_database(database)
    return AppRuntimeEnvironment(
        identity_database=database,
        host="127.0.0.1",
        port=8080,
        session_lifetime=timedelta(hours=1),
    )


def _runtime(
    database: Path,
    oauth: _OAuth | None = None,
    rate_limiter: AppRateLimiter | None = None,
) -> tuple[AppRuntime, _OAuth]:
    fake = oauth or _OAuth()
    environment = _environment(database)
    runtime = AppRuntime(
        environment=environment,
        oauth=cast(GoogleWebOAuthService, fake),
        sessions=CanonicalBrowserSessionAuthority(
            database,
            environment.session_lifetime,
        ),
        browser=WebIdentitySessionBoundary(production_origins=(_ORIGIN,)),
        desktop_client_id="desktop-client-id",
        rate_limiter=rate_limiter,
    )
    return runtime, fake


def _cookie_values(headers: tuple[tuple[str, str], ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in headers:
        if key != "Set-Cookie":
            continue
        cookie = SimpleCookie()
        cookie.load(value)
        values.update({name: morsel.value for name, morsel in cookie.items()})
    return values


def _cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def _callback(runtime: AppRuntime) -> tuple[dict[str, str], str, str]:
    response = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/callback?state=state-value-12345&code=code-value-123456",
            headers={},
        ),
        now=_NOW,
    )
    assert response.status is HTTPStatus.SEE_OTHER
    cookies = _cookie_values(response.headers)
    credential = cookies["__Host-ilaios_auth"]
    session_id = cookies["__Host-ilaios_session"]
    assert cookies["__Host-ilaios_csrf"]
    return cookies, credential, session_id


def test_readiness_and_google_start_use_exact_production_callback(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, oauth = _runtime(database)

    ready = runtime.dispatch(
        RuntimeRequest(method="GET", target="/health/ready", headers={}),
        now=_NOW,
    )
    assert ready.status is HTTPStatus.OK
    assert ready.body == b'{"status":"ready"}'

    start = runtime.dispatch(
        RuntimeRequest(method="GET", target="/auth/google/start", headers={}),
        now=_NOW,
    )
    assert start.status is HTTPStatus.FOUND
    assert oauth.start_redirects == [_CALLBACK]
    location = dict(start.headers)["Location"]
    parsed = urlsplit(location)
    assert parsed.hostname == "accounts.google.com"
    assert parse_qs(parsed.query)["redirect_uri"] == [_CALLBACK]



def test_callback_accepts_google_issuer_parameter(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, oauth = _runtime(database)

    response = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target=(
                "/auth/google/callback?"
                "state=state-value-12345&code=code-value-123456&"
                "iss=https%3A%2F%2Faccounts.google.com"
            ),
            headers={},
        ),
        now=_NOW,
    )
    assert response.status is HTTPStatus.SEE_OTHER
    assert oauth.completions == [("state-value-12345", "code-value-123456")]


@pytest.mark.parametrize(  # type: ignore[misc, unused-ignore]
    ("error", "stage"),
    (
        (
            GoogleWebOAuthStateError("state=state-should-never-be-logged"),
            "oauth_state_rejected",
        ),
        (
            GoogleWebOAuthTokenExchangeError("code=code-should-never-be-logged"),
            "token_exchange_rejected",
        ),
        (
            GoogleWebOAuthIDTokenVerificationError("token-should-never-be-logged"),
            "id_token_verification_rejected",
        ),
        (GoogleWebOAuthJwksResolutionError("token"), "jwks_fetch_or_key_resolution_failed"),
        (GoogleWebOAuthJWTDecodeError("token"), "jwt_signature_or_decode_failed"),
        (GoogleWebOAuthIssuerAudienceError("token"), "issuer_or_audience_rejected"),
        (GoogleWebOAuthNonceError("token"), "nonce_rejected"),
        (GoogleWebOAuthTemporalClaimsError("token"), "temporal_claims_rejected"),
        (GoogleWebOAuthIssuedAtFutureError("token"), "issued_at_future_rejected"),
        (GoogleWebOAuthExpiredTokenError("token"), "expired_token_rejected"),
        (GoogleWebOAuthLifetimeExceededError("token"), "token_lifetime_exceeded"),
        (GoogleWebOAuthMalformedClaimsError("token"), "malformed_claims_rejected"),
    ),
)
def test_oauth_failure_logs_only_safe_stage_and_returns_generic_denial(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    stage: str,
) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db", _FailingOAuth(error))
    caplog.set_level(logging.WARNING, logger=runtime_server.__name__)

    response = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target=(
                "/auth/google/callback?state=state-should-never-be-logged&"
                "code=code-should-never-be-logged"
            ),
            headers={},
        ),
        now=_NOW,
    )

    assert response.status is HTTPStatus.UNAUTHORIZED
    assert response.body == b'{"error":"authentication denied"}'
    assert caplog.messages == [f"app_auth_failure stage={stage}"]
    for unsafe_value in (
        "state-should-never-be-logged",
        "code-should-never-be-logged",
        "token-should-never-be-logged",
    ):
        assert unsafe_value not in caplog.text
        assert unsafe_value.encode() not in response.body


def test_canonical_and_session_failure_log_only_safe_stage(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    caplog.set_level(logging.WARNING, logger=runtime_server.__name__)

    def reject_canonical(*_args: object, **_kwargs: object) -> object:
        raise GoogleWebCanonicalIdentityError("subject-should-never-be-logged")

    monkeypatch.setattr(
        runtime_server.GoogleWebCanonicalIdentityFlow,  # type: ignore[attr-defined]
        "complete",
        reject_canonical,
    )
    canonical = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/callback?state=state&code=code",
            headers={},
        ),
        now=_NOW,
    )
    assert canonical.status is HTTPStatus.UNAUTHORIZED
    assert canonical.body == b'{"error":"authentication denied"}'
    assert caplog.messages == [
        "app_auth_failure stage=canonical_identity_rejected"
    ]
    assert "subject-should-never-be-logged" not in caplog.text

    monkeypatch.undo()
    caplog.clear()

    def reject_session(*_args: object, **_kwargs: object) -> object:
        raise CanonicalBrowserSessionError("credential-should-never-be-logged")

    monkeypatch.setattr(
        CanonicalBrowserSessionAuthority,
        "issue",
        reject_session,
    )
    session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/callback?state=state&code=code",
            headers={},
        ),
        now=_NOW,
    )
    assert session.status is HTTPStatus.UNAUTHORIZED
    assert session.body == b'{"error":"authentication denied"}'
    assert caplog.messages == ["app_auth_failure stage=session_issue_rejected"]
    assert "credential-should-never-be-logged" not in caplog.text


def test_successful_callback_does_not_emit_auth_failure_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    caplog.set_level(logging.WARNING, logger=runtime_server.__name__)

    _callback(runtime)

    assert caplog.messages == []


def test_callback_issues_digest_only_canonical_session_and_safe_metadata(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)

    cookies, credential, session_id = _callback(runtime)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT user_id, tenant_id, credential_hash, revoked_at
              FROM identity_sessions
             WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    assert row is not None
    assert row[2] == hashlib.sha256(credential.encode()).hexdigest()
    assert row[2] != credential
    assert row[3] is None

    session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert session.status is HTTPStatus.OK
    assert credential.encode() not in session.body
    assert row[2].encode() not in session.body
    assert b'"authenticated":true' in session.body
    assert b'"OWNER"' in session.body


def test_returning_google_subject_keeps_same_user_and_tenant(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)

    first_cookies, _, first_session = _callback(runtime)
    first = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(first_cookies)},
        ),
        now=_NOW,
    )

    second_cookies, _, second_session = _callback(runtime)
    second = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(second_cookies)},
        ),
        now=_NOW,
    )

    assert first_session != second_session
    assert first.body == second.body




def test_desktop_google_canonicalization_returns_same_canonical_account(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    cookies, _, _ = _callback(runtime)

    web_session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert web_session.status is HTTPStatus.OK
    web_payload = json.loads(web_session.body)

    observed: dict[str, object] = {}

    def verify_desktop(
        encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        observed["token"] = encoded_token
        observed["client_id"] = client_id
        observed["now"] = now
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="google-subject-123",
            email="owner@example.com",
            email_verified=True,
        )

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        verify_desktop,
    )
    desktop = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/desktop/canonicalize",
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "provider_id": "google",
                    "id_token": "token",
                }
            ).encode(),
        ),
        now=_NOW,
    )

    assert desktop.status is HTTPStatus.OK
    desktop_payload = json.loads(desktop.body)
    assert desktop_payload["user_id"] == web_payload["user_id"]
    assert desktop_payload["tenant_id"] == web_payload["tenant_id"]
    assert observed == {
        "token": "token",
        "client_id": "desktop-client-id",
        "now": _NOW,
    }


def test_desktop_canonicalization_rejects_bad_body_and_hides_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    malformed = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/desktop/canonicalize",
            headers={"Content-Type": "text/plain"},
            body=b"not-json",
        ),
        now=_NOW,
    )
    assert malformed.status is HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    token = "test-token"

    def reject_desktop(
        _encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        assert client_id == "desktop-client-id"
        assert now == _NOW
        raise GoogleDesktopIdentityVerificationError(token)

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        reject_desktop,
    )
    caplog.set_level(logging.WARNING, logger=runtime_server.__name__)
    denied = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/desktop/canonicalize",
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {"provider_id": "google", "id_token": token}
            ).encode(),
        ),
        now=_NOW,
    )
    assert denied.status is HTTPStatus.UNAUTHORIZED
    assert denied.body == b'{"error":"authentication denied"}'
    assert caplog.messages == ["app_auth_failure stage=desktop_id_token_rejected"]
    assert token not in caplog.text
    assert token.encode() not in denied.body


def test_logout_page_requires_authenticated_session_and_uses_safe_same_origin_script(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)

    denied = runtime.dispatch(
        RuntimeRequest(method="GET", target="/auth/logout", headers={}),
        now=_NOW,
    )
    assert denied.status is HTTPStatus.FORBIDDEN

    cookies, _, _ = _callback(runtime)
    page = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/logout",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert page.status is HTTPStatus.OK
    headers = dict(page.headers)
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    csp = headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert b"/auth/logout.js" in page.body
    assert cookies["__Host-ilaios_csrf"].encode() not in page.body
    assert cookies["__Host-ilaios_auth"].encode() not in page.body

    script = runtime.dispatch(
        RuntimeRequest(method="GET", target="/auth/logout.js", headers={}),
        now=_NOW,
    )
    assert script.status is HTTPStatus.OK
    assert dict(script.headers)["Content-Type"] == "text/javascript; charset=utf-8"
    assert b"X-CSRF-Token" in script.body
    assert b"credentials:'same-origin'" in script.body
    assert b"window.location.replace('/auth/session')" in script.body
    assert cookies["__Host-ilaios_csrf"].encode() not in script.body
    assert cookies["__Host-ilaios_auth"].encode() not in script.body


def test_logout_get_does_not_revoke_session(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    cookies, credential, session_id = _callback(runtime)

    page = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/logout",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert page.status is HTTPStatus.OK
    principal = runtime.sessions.verify(session_id, credential, _NOW)
    assert principal.principal_id


def test_logout_requires_origin_csrf_revokes_and_clears_all_cookies(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    cookies, credential, session_id = _callback(runtime)
    cookie_header = _cookie_header(cookies)
    csrf = cookies["__Host-ilaios_csrf"]

    denied = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/logout",
            headers={
                "Cookie": cookie_header,
                "Origin": "https://evil.example",
                "X-CSRF-Token": csrf,
            },
        ),
        now=_NOW,
    )
    assert denied.status is HTTPStatus.FORBIDDEN

    missing_csrf = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/logout",
            headers={"Cookie": cookie_header, "Origin": _ORIGIN},
        ),
        now=_NOW,
    )
    assert missing_csrf.status is HTTPStatus.FORBIDDEN

    logout = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/logout",
            headers={
                "Cookie": cookie_header,
                "Origin": _ORIGIN,
                "X-CSRF-Token": csrf,
            },
        ),
        now=_NOW,
    )
    assert logout.status is HTTPStatus.NO_CONTENT
    clear_headers = [value for key, value in logout.headers if key == "Set-Cookie"]
    assert len(clear_headers) == 3
    assert all("Max-Age=0" in value for value in clear_headers)

    with pytest.raises(PermissionError):
        runtime.sessions.verify(session_id, credential, _NOW + timedelta(seconds=1))


def test_valid_session_survives_runtime_reconstruction(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, oauth = _runtime(database)
    cookies, _, _ = _callback(runtime)

    reconstructed, _ = _runtime(database, oauth)
    response = reconstructed.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(minutes=1),
    )
    assert response.status is HTTPStatus.OK


def test_session_denies_authorization_header_wrong_credential_and_digest(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    cookies, credential, session_id = _callback(runtime)

    injected = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={
                "Cookie": _cookie_header(cookies),
                "Authorization": "Bearer attacker",
            },
        ),
        now=_NOW,
    )
    assert injected.status is HTTPStatus.FORBIDDEN

    cookies["__Host-ilaios_auth"] = "x" * len(credential)
    wrong = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert wrong.status is HTTPStatus.UNAUTHORIZED

    with sqlite3.connect(database) as connection:
        digest = str(
            connection.execute(
                "SELECT credential_hash FROM identity_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        )
    cookies["__Host-ilaios_auth"] = digest
    digest_attempt = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert digest_attempt.status is HTTPStatus.UNAUTHORIZED


def test_disabled_user_suspended_membership_and_expiry_fail_closed(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    cookies, _, _ = _callback(runtime)

    with sqlite3.connect(database) as connection:
        user_id = str(
            connection.execute("SELECT user_id FROM identity_sessions").fetchone()[0]
        )
        connection.execute(
            "UPDATE identity_users SET enabled = 0 WHERE user_id = ?",
            (user_id,),
        )
        connection.commit()

    disabled = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert disabled.status is HTTPStatus.UNAUTHORIZED

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_users SET enabled = 1 WHERE user_id = ?",
            (user_id,),
        )
        connection.execute(
            "UPDATE identity_memberships SET status = 'SUSPENDED' WHERE user_id = ?",
            (user_id,),
        )
        connection.commit()

    suspended = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert suspended.status is HTTPStatus.UNAUTHORIZED

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status = 'ACTIVE' WHERE user_id = ?",
            (user_id,),
        )
        connection.commit()

    expired = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(hours=1),
    )
    assert expired.status is HTTPStatus.UNAUTHORIZED


def test_callback_rejects_missing_duplicate_or_authority_query_inputs(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)

    for target in (
        "/auth/google/callback",
        "/auth/google/callback?state=x",
        "/auth/google/callback?code=x",
        "/auth/google/callback?state=a&state=b&code=c",
        "/auth/google/callback?state=a&code=b&user_id=attacker",
        "/auth/google/callback?state=a&code=b&tenant_id=attacker",
        "/auth/google/callback?state=a&code=b&role=OWNER",
    ):
        response = runtime.dispatch(
            RuntimeRequest(method="GET", target=target, headers={}),
            now=_NOW,
        )
        assert response.status is HTTPStatus.BAD_REQUEST


def test_unknown_route_and_unsupported_methods_are_bounded(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)

    unknown = runtime.dispatch(
        RuntimeRequest(method="GET", target="/does-not-exist", headers={}),
        now=_NOW,
    )
    assert unknown.status is HTTPStatus.NOT_FOUND

    wrong_method = runtime.dispatch(
        RuntimeRequest(method="PUT", target="/auth/logout", headers={}),
        now=_NOW,
    )
    assert wrong_method.status is HTTPStatus.METHOD_NOT_ALLOWED
    assert dict(wrong_method.headers)["Allow"] == "GET, POST"



def test_auth_rate_limit_is_bounded_per_source_and_path(tmp_path: Path) -> None:
    limiter = AppRateLimiter({"/auth/google/start": (2, 60)})
    runtime, _oauth = _runtime(tmp_path / "identity.db", rate_limiter=limiter)

    first = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={},
            source="198.51.100.10",
        ),
        now=_NOW,
    )
    second = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={},
            source="198.51.100.10",
        ),
        now=_NOW + timedelta(seconds=1),
    )
    limited = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={},
            source="198.51.100.10",
        ),
        now=_NOW + timedelta(seconds=2),
    )
    other_source = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={},
            source="198.51.100.11",
        ),
        now=_NOW + timedelta(seconds=2),
    )

    assert first.status is HTTPStatus.FOUND
    assert second.status is HTTPStatus.FOUND
    assert limited.status is HTTPStatus.TOO_MANY_REQUESTS
    assert limited.body == b'{"error":"rate limit exceeded"}'
    assert dict(limited.headers)["Retry-After"] == "58"
    assert other_source.status is HTTPStatus.FOUND


def test_auth_rate_limit_window_recovers_and_health_is_not_limited(tmp_path: Path) -> None:
    limiter = AppRateLimiter({"/auth/session": (1, 10)})
    runtime, _oauth = _runtime(tmp_path / "identity.db", rate_limiter=limiter)

    first = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={},
            source="203.0.113.7",
        ),
        now=_NOW,
    )
    limited = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={},
            source="203.0.113.7",
        ),
        now=_NOW + timedelta(seconds=1),
    )
    recovered = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={},
            source="203.0.113.7",
        ),
        now=_NOW + timedelta(seconds=10),
    )
    ready = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/health/ready",
            headers={},
            source="203.0.113.7",
        ),
        now=_NOW + timedelta(seconds=1),
    )

    assert first.status is HTTPStatus.FORBIDDEN
    assert limited.status is HTTPStatus.TOO_MANY_REQUESTS
    assert dict(limited.headers)["Retry-After"] == "9"
    assert recovered.status is HTTPStatus.FORBIDDEN
    assert ready.status is HTTPStatus.OK


def test_rate_limiter_ignores_untrusted_forwarding_headers(tmp_path: Path) -> None:
    limiter = AppRateLimiter({"/auth/google/start": (1, 60)})
    runtime, _oauth = _runtime(tmp_path / "identity.db", rate_limiter=limiter)

    first = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={"X-Forwarded-For": "198.51.100.1"},
            source="192.0.2.10",
        ),
        now=_NOW,
    )
    spoofed = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/start",
            headers={"X-Forwarded-For": "198.51.100.2"},
            source="192.0.2.10",
        ),
        now=_NOW + timedelta(seconds=1),
    )

    assert first.status is HTTPStatus.FOUND
    assert spoofed.status is HTTPStatus.TOO_MANY_REQUESTS


def test_environment_requires_database_and_valid_runtime_bounds(tmp_path: Path) -> None:
    with pytest.raises(AppRuntimeConfigurationError):
        AppRuntimeEnvironment.from_environment({})

    with pytest.raises(AppRuntimeConfigurationError):
        AppRuntimeEnvironment.from_environment(
            {
                "ILAIOS_IDENTITY_DATABASE_PATH": str(tmp_path / "identity.db"),
                "ILAIOS_APP_HTTP_PORT": "70000",
            }
        )

    with pytest.raises(AppRuntimeConfigurationError):
        AppRuntimeEnvironment.from_environment(
            {
                "ILAIOS_IDENTITY_DATABASE_PATH": str(tmp_path / "identity.db"),
                "ILAIOS_WEB_SESSION_LIFETIME_SECONDS": "86401",
            }
        )


def test_environment_uses_platform_port_when_app_port_is_absent(tmp_path: Path) -> None:
    environment = AppRuntimeEnvironment.from_environment(
        {
            "ILAIOS_IDENTITY_DATABASE_PATH": str(tmp_path / "identity.db"),
            "PORT": "10000",
        }
    )

    assert environment.host == "0.0.0.0"
    assert environment.port == 10000



def test_rate_limiter_prunes_expired_source_buckets_and_stays_bounded() -> None:
    limiter = AppRateLimiter({"/auth/google/start": (2, 60)}, max_buckets=3)

    for index in range(3):
        assert (
            limiter.check(
                source=f"203.0.113.{index}",
                path="/auth/google/start",
                now=_NOW,
            )
            is None
        )
    assert limiter.bucket_count == 3

    assert (
        limiter.check(
            source="198.51.100.9",
            path="/auth/google/start",
            now=_NOW,
        )
        == 60
    )
    assert limiter.bucket_count == 3

    recovered = _NOW + timedelta(seconds=61)
    assert (
        limiter.check(
            source="198.51.100.9",
            path="/auth/google/start",
            now=recovered,
        )
        is None
    )
    assert limiter.bucket_count == 1


def test_rate_limiter_rejects_unbounded_bucket_configuration() -> None:
    with pytest.raises(ValueError, match="bucket bound"):
        AppRateLimiter({"/auth/google/start": (2, 60)}, max_buckets=0)


def test_app_http_server_has_bounded_concurrency(tmp_path: Path) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    server = AppHTTPServer(
        ("127.0.0.1", 0),
        runtime,
        max_concurrent_requests=2,
    )
    try:
        assert server.max_concurrent_requests == 2
    finally:
        server.server_close()

    with pytest.raises(ValueError, match="concurrent request bound"):
        AppHTTPServer(
            ("127.0.0.1", 0),
            runtime,
            max_concurrent_requests=0,
        )


def test_desktop_canonicalization_projects_li_only_for_exact_founder_account(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "identity.db"
    runtime, _oauth = _runtime(database)
    founder_cookies, _, _ = _callback(runtime)
    founder_session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(founder_cookies)},
        ),
        now=_NOW,
    )
    founder = json.loads(founder_session.body)
    runtime.li = LiFounderOperator(
        config=LiFounderConfig(
            user_id=str(founder["user_id"]),
            tenant_id=str(founder["tenant_id"]),
            database_path=tmp_path / "li.db",
        ),
        identity_database=database,
    )

    def verify_founder(
        _encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        assert client_id == "desktop-client-id"
        assert now == _NOW
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="google-subject-123",
            email="owner@example.com",
            email_verified=True,
        )

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        verify_founder,
    )
    founder_desktop = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/desktop/canonicalize",
            headers={"Content-Type": "application/json"},
            body=b'{"provider_id":"google","id_token":"founder-token"}',
        ),
        now=_NOW,
    )
    assert founder_desktop.status is HTTPStatus.OK
    founder_payload = json.loads(founder_desktop.body)
    assert founder_payload["user_id"] == founder["user_id"]
    assert founder_payload["tenant_id"] == founder["tenant_id"]
    assert founder_payload["li_founder"] is True

    def verify_customer(
        _encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        assert client_id == "desktop-client-id"
        assert now == _NOW
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="customer-google-subject",
            email="customer@example.com",
            email_verified=True,
        )

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        verify_customer,
    )
    customer_desktop = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/auth/desktop/canonicalize",
            headers={"Content-Type": "application/json"},
            body=b'{"provider_id":"google","id_token":"customer-token"}',
        ),
        now=_NOW,
    )
    assert customer_desktop.status is HTTPStatus.OK
    customer_payload = json.loads(customer_desktop.body)
    assert customer_payload["user_id"] != founder_payload["user_id"]
    assert customer_payload["tenant_id"] != founder_payload["tenant_id"]
    assert customer_payload["li_founder"] is False
    with sqlite3.connect(database) as connection:
        role = connection.execute(
            "SELECT role FROM identity_memberships WHERE user_id = ? AND tenant_id = ?",
            (customer_payload["user_id"], customer_payload["tenant_id"]),
        ).fetchone()
    assert role == ("OWNER",)
