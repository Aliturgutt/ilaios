from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import cast

from apps.web_app_runtime.server import (
    AppRuntime,
    AppRuntimeEnvironment,
    RuntimeRequest,
)
from services.canonical_browser_session import CanonicalBrowserSessionAuthority
from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.control_plane.migrations import migrate_database
from services.github_web_oauth import (
    GitHubWebOAuthCompletion,
    GitHubWebOAuthService,
    GitHubWebOAuthStart,
)
from services.google_web_oauth import GoogleWebOAuthService, GoogleWebOAuthStart
from services.microsoft_web_oauth import (
    MicrosoftWebOAuthCompletion,
    MicrosoftWebOAuthService,
    MicrosoftWebOAuthStart,
)
from services.web_identity_session_http import WebIdentitySessionBoundary

_NOW = datetime(2026, 8, 30, 13, 0, tzinfo=UTC)
_ORIGIN = "https://app.ilaios.com"


class _GoogleOAuth:
    def __init__(self, subject: str = "google-user-1") -> None:
        self.subject = subject

    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
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
        assert state
        assert code
        assert now.tzinfo is not None
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject=self.subject,
            email="owner@example.com",
            email_verified=True,
        )


class _MicrosoftOAuth:
    def __init__(
        self,
        *,
        subject: str = "11111111-2222-3333-4444-555555555555",
    ) -> None:
        self.subject = subject
        self.purpose = "signin"

    def start(
        self,
        *,
        redirect_uri: str,
        now: datetime,
        purpose: str = "signin",
    ) -> MicrosoftWebOAuthStart:
        self.purpose = purpose
        return MicrosoftWebOAuthStart(
            state=f"microsoft-{purpose}-state",
            authorization_url=(
                "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"redirect_uri={redirect_uri}"
            ),
            expires_at=now + timedelta(minutes=5),
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        redirect_uri: str,
        now: datetime,
    ) -> MicrosoftWebOAuthCompletion:
        assert state
        assert code
        assert redirect_uri.endswith("/auth/microsoft/callback")
        assert now.tzinfo is not None
        return MicrosoftWebOAuthCompletion(
            identity=VerifiedExternalIdentity(
                provider=IdentityProvider.MICROSOFT,
                subject=self.subject,
                issuer=(
                    "https://login.microsoftonline.com/"
                    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/v2.0"
                ),
            ),
            purpose=self.purpose,
        )


class _GitHubOAuth:
    def __init__(self, *, subject: str = "123456789") -> None:
        self.subject = subject
        self.purpose = "signin"

    def start(
        self,
        *,
        redirect_uri: str,
        now: datetime,
        purpose: str = "signin",
    ) -> GitHubWebOAuthStart:
        self.purpose = purpose
        return GitHubWebOAuthStart(
            state=f"github-{purpose}-state",
            authorization_url=(
                "https://github.com/login/oauth/authorize?"
                f"redirect_uri={redirect_uri}"
            ),
            expires_at=now + timedelta(minutes=5),
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        redirect_uri: str,
        now: datetime,
    ) -> GitHubWebOAuthCompletion:
        assert state
        assert code
        assert redirect_uri.endswith("/auth/github/callback")
        assert now.tzinfo is not None
        return GitHubWebOAuthCompletion(
            identity=VerifiedExternalIdentity(
                provider=IdentityProvider.GITHUB,
                subject=self.subject,
                email="owner@example.com",
                email_verified=True,
            ),
            purpose=self.purpose,
        )


def _runtime(
    database: Path,
    *,
    microsoft: _MicrosoftOAuth | None = None,
    github: _GitHubOAuth | None = None,
) -> AppRuntime:
    migrate_database(database)
    environment = AppRuntimeEnvironment(
        identity_database=database,
        host="127.0.0.1",
        port=8080,
        session_lifetime=timedelta(hours=1),
    )
    return AppRuntime(
        environment=environment,
        oauth=cast(GoogleWebOAuthService, _GoogleOAuth()),
        sessions=CanonicalBrowserSessionAuthority(
            database,
            environment.session_lifetime,
        ),
        browser=WebIdentitySessionBoundary(production_origins=(_ORIGIN,)),
        desktop_client_id="desktop-client-id",
        microsoft_oauth=(
            None if microsoft is None else cast(MicrosoftWebOAuthService, microsoft)
        ),
        github_oauth=None if github is None else cast(GitHubWebOAuthService, github),
    )


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


def _google_login(runtime: AppRuntime) -> tuple[dict[str, str], dict[str, object]]:
    callback = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/callback?state=state-value-12345&code=code-value-12345",
            headers={},
        ),
        now=_NOW,
    )
    assert callback.status is HTTPStatus.SEE_OTHER
    cookies = _cookie_values(callback.headers)
    session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert session.status is HTTPStatus.OK
    return cookies, json.loads(session.body)


def test_provider_catalog_only_advertises_configured_providers(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path / "identity.db",
        microsoft=_MicrosoftOAuth(),
        github=_GitHubOAuth(),
    )
    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/auth/providers", headers={}),
        now=_NOW,
    )
    assert response.status is HTTPStatus.OK
    assert json.loads(response.body) == {
        "providers": ["google", "microsoft", "github"]
    }


def test_returning_microsoft_identity_keeps_same_canonical_account(
    tmp_path: Path,
) -> None:
    microsoft = _MicrosoftOAuth()
    runtime = _runtime(tmp_path / "identity.db", microsoft=microsoft)

    first = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/microsoft/callback?state=state-one&code=code-one-value",
            headers={},
        ),
        now=_NOW,
    )
    assert first.status is HTTPStatus.SEE_OTHER
    first_cookies = _cookie_values(first.headers)
    first_session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(first_cookies)},
        ),
        now=_NOW,
    )

    second = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/microsoft/callback?state=state-two&code=code-two-value",
            headers={},
        ),
        now=_NOW + timedelta(seconds=2),
    )
    assert second.status is HTTPStatus.SEE_OTHER
    second_cookies = _cookie_values(second.headers)
    second_session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(second_cookies)},
        ),
        now=_NOW + timedelta(seconds=2),
    )

    assert json.loads(first_session.body) == json.loads(second_session.body)


def test_github_link_flow_binds_to_existing_google_user_and_tenant(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    github = _GitHubOAuth()
    runtime = _runtime(database, github=github)
    cookies, google_session = _google_login(runtime)

    start = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/link/github/start",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(minutes=1),
    )
    assert start.status is HTTPStatus.FOUND
    assert github.purpose == "link"

    linked = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/github/callback?state=link-state-value&code=link-code-value",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(minutes=1, seconds=5),
    )
    assert linked.status is HTTPStatus.SEE_OTHER

    after = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(minutes=1, seconds=5),
    )
    assert json.loads(after.body) == google_session

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT provider, user_id, tenant_id FROM identity_accounts "
            "ORDER BY provider"
        ).fetchall()
    assert [row[0] for row in rows] == ["github", "google"]
    assert len({row[1] for row in rows}) == 1
    assert len({row[2] for row in rows}) == 1
    assert rows[0][1] == google_session["user_id"]
    assert rows[0][2] == google_session["tenant_id"]


def test_same_email_never_auto_merges_unlinked_provider_identity(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    github = _GitHubOAuth()
    runtime = _runtime(database, github=github)
    _cookies, google_session = _google_login(runtime)

    github_login = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/github/callback?state=signin-state-value&code=signin-code-value",
            headers={},
        ),
        now=_NOW + timedelta(seconds=5),
    )
    assert github_login.status is HTTPStatus.SEE_OTHER
    github_cookies = _cookie_values(github_login.headers)
    github_session = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/session",
            headers={"Cookie": _cookie_header(github_cookies)},
        ),
        now=_NOW + timedelta(seconds=5),
    )
    github_payload = json.loads(github_session.body)

    assert github_payload["user_id"] != google_session["user_id"]
    assert github_payload["tenant_id"] != google_session["tenant_id"]


def test_linking_requires_recent_authenticated_session(tmp_path: Path) -> None:
    github = _GitHubOAuth()
    runtime = _runtime(tmp_path / "identity.db", github=github)

    denied = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/link/github/start",
            headers={},
        ),
        now=_NOW,
    )
    assert denied.status is HTTPStatus.FORBIDDEN

    cookies, _session = _google_login(runtime)
    stale = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/link/github/start",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW + timedelta(minutes=11),
    )
    assert stale.status is HTTPStatus.UNAUTHORIZED
    assert stale.body == b'{"error":"authentication denied"}'

def test_github_standard_error_uri_callback_is_not_rejected_as_unexpected_query(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "identity.db", github=_GitHubOAuth())

    response = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target=(
                "/auth/github/callback?"
                "error=redirect_uri_mismatch&"
                "error_description=callback+mismatch&"
                "error_uri=https%3A%2F%2Fdocs.github.com%2Foauth&"
                "state=github-signin-state"
            ),
            headers={},
        ),
        now=_NOW,
    )

    assert response.status is HTTPStatus.UNAUTHORIZED
    assert response.body == b'{"error":"authentication denied"}'

