from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import cast

import apps.web_app_runtime.server as runtime_server
import pytest
from apps.web_app_runtime.server import (
    AppRuntime,
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
from services.li_founder_operator import LiFounderConfig, LiFounderOperator
from services.web_identity_session_http import WebIdentitySessionBoundary

_NOW = datetime(2026, 8, 31, 1, 0, tzinfo=UTC)
_ORIGIN = "https://app.ilaios.com"


class _OAuth:
    def __init__(self) -> None:
        self.subject = "founder-google-subject"

    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
        return GoogleWebOAuthStart(
            state="li-state",
            authorization_url=(
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"redirect_uri={redirect_uri}&state=li-state"
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
            email=f"{self.subject}@example.com",
            email_verified=True,
        )


def _runtime(database: Path) -> tuple[AppRuntime, _OAuth]:
    migrate_database(database)
    environment = AppRuntimeEnvironment(
        identity_database=database,
        host="127.0.0.1",
        port=8080,
        session_lifetime=timedelta(hours=1),
    )
    oauth = _OAuth()
    runtime = AppRuntime(
        environment=environment,
        oauth=cast(GoogleWebOAuthService, oauth),
        sessions=CanonicalBrowserSessionAuthority(
            database,
            environment.session_lifetime,
        ),
        browser=WebIdentitySessionBoundary(production_origins=(_ORIGIN,)),
        desktop_client_id="desktop-client-id",
    )
    return runtime, oauth


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


def _login(runtime: AppRuntime) -> tuple[dict[str, str], dict[str, object]]:
    callback = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/auth/google/callback?state=li-state&code=li-code",
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


def _enable_li(
    runtime: AppRuntime,
    *,
    li_database: Path,
    session: dict[str, object],
) -> LiFounderConfig:
    config = LiFounderConfig(
        user_id=str(session["user_id"]),
        tenant_id=str(session["tenant_id"]),
        database_path=li_database,
    )
    runtime.li = LiFounderOperator(
        config=config,
        identity_database=runtime.environment.identity_database,
        runtime_environment={"ILAIOS_RELEASE_SHA": "b" * 40},
    )
    return config


def test_founder_li_surface_memory_and_live_state_are_session_bound(
    tmp_path: Path,
) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    cookies, session = _login(runtime)
    config = _enable_li(
        runtime,
        li_database=tmp_path / "li.db",
        session=session,
    )
    cookie_header = _cookie_header(cookies)

    page = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/li",
            headers={"Cookie": cookie_header},
        ),
        now=_NOW,
    )
    assert page.status is HTTPStatus.OK
    assert b"<h1>Li</h1>" in page.body
    assert b"/li/app.js" in page.body

    script = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/li/app.js",
            headers={"Cookie": cookie_header},
        ),
        now=_NOW,
    )
    assert script.status is HTTPStatus.OK
    assert b"/api/li/state" in script.body
    assert b"X-CSRF-Token" in script.body

    state = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/api/li/state",
            headers={"Cookie": cookie_header},
        ),
        now=_NOW,
    )
    assert state.status is HTTPStatus.OK
    state_payload = json.loads(state.body)
    assert state_payload["name"] == "Li"
    assert state_payload["memory_count"] == 0
    assert state_payload["system"]["release_sha"] == "b" * 40

    denied_without_csrf = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/li/memories",
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": _ORIGIN,
            },
            body=b'{"kind":"semantic","content":"Founder memory"}',
        ),
        now=_NOW,
    )
    assert denied_without_csrf.status is HTTPStatus.FORBIDDEN

    stored = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/li/memories",
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": _ORIGIN,
                "X-CSRF-Token": cookies["__Host-ilaios_csrf"],
            },
            body=b'{"kind":"semantic","content":"Founder memory"}',
        ),
        now=_NOW,
    )
    assert stored.status is HTTPStatus.CREATED

    memories = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/api/li/memories",
            headers={"Cookie": cookie_header},
        ),
        now=_NOW,
    )
    assert memories.status is HTTPStatus.OK
    assert json.loads(memories.body)["memories"][0]["content"] == "Founder memory"

    runtime.li = LiFounderOperator(
        config=config,
        identity_database=runtime.environment.identity_database,
    )
    after_restart = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/api/li/memories",
            headers={"Cookie": cookie_header},
        ),
        now=_NOW,
    )
    assert after_restart.status is HTTPStatus.OK
    assert json.loads(after_restart.body)["memories"][0]["content"] == "Founder memory"


def test_customer_owner_cannot_discover_or_use_founder_li_data(tmp_path: Path) -> None:
    runtime, oauth = _runtime(tmp_path / "identity.db")
    founder_cookies, founder_session = _login(runtime)
    _enable_li(
        runtime,
        li_database=tmp_path / "li.db",
        session=founder_session,
    )
    founder_cookie_header = _cookie_header(founder_cookies)

    stored = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/li/memories",
            headers={
                "Cookie": founder_cookie_header,
                "Content-Type": "application/json",
                "Origin": _ORIGIN,
                "X-CSRF-Token": founder_cookies["__Host-ilaios_csrf"],
            },
            body=b'{"kind":"episodic","content":"Founder-only evidence"}',
        ),
        now=_NOW,
    )
    assert stored.status is HTTPStatus.CREATED

    oauth.subject = "customer-google-subject"
    customer_cookies, customer_session = _login(runtime)
    assert customer_session["user_id"] != founder_session["user_id"]
    assert customer_session["tenant_id"] != founder_session["tenant_id"]
    customer_cookie_header = _cookie_header(customer_cookies)

    for target in ("/li", "/li/app.js", "/api/li/state", "/api/li/memories"):
        denied = runtime.dispatch(
            RuntimeRequest(
                method="GET",
                target=target,
                headers={"Cookie": customer_cookie_header},
            ),
            now=_NOW,
        )
        assert denied.status is HTTPStatus.FORBIDDEN
        assert b"Founder-only evidence" not in denied.body

    denied_write = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/li/memories",
            headers={
                "Cookie": customer_cookie_header,
                "Content-Type": "application/json",
                "Origin": _ORIGIN,
                "X-CSRF-Token": customer_cookies["__Host-ilaios_csrf"],
            },
            body=b'{"kind":"semantic","content":"customer probe"}',
        ),
        now=_NOW,
    )
    assert denied_write.status is HTTPStatus.FORBIDDEN


def test_li_routes_fail_closed_when_feature_is_not_configured(tmp_path: Path) -> None:
    runtime, _oauth = _runtime(tmp_path / "identity.db")
    cookies, _session = _login(runtime)
    response = runtime.dispatch(
        RuntimeRequest(
            method="GET",
            target="/li",
            headers={"Cookie": _cookie_header(cookies)},
        ),
        now=_NOW,
    )
    assert response.status is HTTPStatus.FORBIDDEN


def test_desktop_li_memory_api_reauthenticates_and_denies_customer_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, oauth = _runtime(tmp_path / "identity.db")
    _cookies, founder_session = _login(runtime)
    _enable_li(
        runtime,
        li_database=tmp_path / "li.db",
        session=founder_session,
    )

    def founder_token(
        _encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        assert client_id == "desktop-client-id"
        assert now == _NOW
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject=oauth.subject,
            email=f"{oauth.subject}@example.com",
            email_verified=True,
        )

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        founder_token,
    )
    stored = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/desktop/li/memories/remember",
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "provider_id": "google",
                    "id_token": "founder-token",
                    "kind": "semantic",
                    "content": "Desktop founder memory",
                }
            ).encode(),
        ),
        now=_NOW,
    )
    assert stored.status is HTTPStatus.CREATED
    stored_payload = json.loads(stored.body)
    assert stored_payload["content"] == "Desktop founder memory"
    assert stored_payload["source"] == "desktop"

    listed = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/desktop/li/memories/list",
            headers={"Content-Type": "application/json"},
            body=b'{"provider_id":"google","id_token":"founder-token"}',
        ),
        now=_NOW,
    )
    assert listed.status is HTTPStatus.OK
    assert json.loads(listed.body)["memories"][0]["content"] == "Desktop founder memory"

    def customer_token(
        _encoded_token: str,
        *,
        client_id: str,
        now: datetime,
    ) -> VerifiedExternalIdentity:
        assert client_id == "desktop-client-id"
        assert now == _NOW
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="customer-desktop-subject",
            email="customer-desktop@example.com",
            email_verified=True,
        )

    monkeypatch.setattr(
        runtime_server,
        "verify_google_desktop_id_token",
        customer_token,
    )
    denied = runtime.dispatch(
        RuntimeRequest(
            method="POST",
            target="/api/desktop/li/memories/list",
            headers={"Content-Type": "application/json"},
            body=b'{"provider_id":"google","id_token":"customer-token"}',
        ),
        now=_NOW,
    )
    assert denied.status is HTTPStatus.FORBIDDEN
    assert b"Desktop founder memory" not in denied.body
