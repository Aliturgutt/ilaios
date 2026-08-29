from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest

from apps.web_app_runtime.server import (
    AppRuntime,
    AppRuntimeConfigurationError,
    AppRuntimeEnvironment,
    RuntimeRequest,
)
from services.canonical_browser_session import CanonicalBrowserSessionAuthority
from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.control_plane.migrations import migrate_database
from services.google_web_oauth import (
    GoogleWebOAuthService,
    GoogleWebOAuthStart,
)
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


def _environment(database: Path) -> AppRuntimeEnvironment:
    migrate_database(database)
    return AppRuntimeEnvironment(
        identity_database=database,
        host="127.0.0.1",
        port=8080,
        session_lifetime=timedelta(hours=1),
    )


def _runtime(database: Path, oauth: _OAuth | None = None) -> tuple[AppRuntime, _OAuth]:
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
        RuntimeRequest(method="GET", target="/auth/logout", headers={}),
        now=_NOW,
    )
    assert wrong_method.status is HTTPStatus.METHOD_NOT_ALLOWED
    assert dict(wrong_method.headers)["Allow"] == "POST"


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
