from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import cast

from apps.web_app_runtime.login_server import LoginAppRuntime
from apps.web_app_runtime.server import AppRuntimeEnvironment, RuntimeRequest
from services.canonical_browser_session import CanonicalBrowserSessionAuthority
from services.control_plane.migrations import migrate_database
from services.google_web_oauth import GoogleWebOAuthService, GoogleWebOAuthStart
from services.web_identity_session_http import WebIdentitySessionBoundary

_NOW = datetime(2026, 9, 2, 15, 0, tzinfo=UTC)
_ORIGIN = "https://app.ilaios.com"
_CALLBACK = "https://app.ilaios.com/auth/google/callback"


class _OAuth:
    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
        return GoogleWebOAuthStart(
            state="goa_test.0.login-state",
            authorization_url=(
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"redirect_uri={redirect_uri}&state=goa_test.0.login-state"
            ),
            expires_at=now + timedelta(minutes=5),
        )


def _runtime(database: Path) -> LoginAppRuntime:
    migrate_database(database)
    environment = AppRuntimeEnvironment(
        identity_database=database,
        host="127.0.0.1",
        port=8080,
        session_lifetime=timedelta(hours=1),
    )
    return LoginAppRuntime(
        environment=environment,
        oauth=cast(GoogleWebOAuthService, _OAuth()),
        sessions=CanonicalBrowserSessionAuthority(
            database,
            environment.session_lifetime,
        ),
        browser=WebIdentitySessionBoundary(production_origins=(_ORIGIN,)),
        desktop_client_id="desktop-client-id",
    )


def test_root_is_light_first_login_with_optional_dark_mode(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/", headers={}),
        now=_NOW,
    )

    assert response.status is HTTPStatus.OK
    assert dict(response.headers)["Content-Type"] == "text/html; charset=utf-8"
    assert dict(response.headers)["Cache-Control"] == "no-store"
    csp = dict(response.headers)["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    document = response.body.decode("utf-8")
    assert '<html lang="en" data-theme="light">' in document
    assert "Welcome back" in document
    assert "Sign in to ILAIOS" not in document
    assert "Choose an account to continue." in document
    assert 'href="/auth/google/start"' in document
    assert 'href="/auth/microsoft/start"' in document
    assert 'href="/auth/github/start"' in document
    assert 'id="theme-light"' in document
    assert 'id="theme-dark"' in document
    assert '<script src="/login/app.js" defer></script>' in document
    assert "<style" not in document


def test_dark_logo_blends_with_canonical_carbon_background(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/login/styles.css", headers={}),
        now=_NOW,
    )

    assert response.status is HTTPStatus.OK
    assert dict(response.headers)["Content-Type"] == "text/css; charset=utf-8"
    stylesheet = response.body.decode("utf-8")
    assert '--bg:#0A0A0A' in stylesheet
    assert '.brand-image-dark{display:none;background:#0A0A0A}' in stylesheet
    assert 'html[data-theme="dark"] .brand-lockup{background:#0A0A0A}' in stylesheet
    assert '#0B0E13' not in stylesheet
    assert 'mix-blend-mode' not in stylesheet


def test_login_heading_uses_refined_corporate_typography(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/login/styles.css", headers={}),
        now=_NOW,
    )

    stylesheet = response.body.decode("utf-8")
    assert 'font-family:"Segoe UI Variable Display","Segoe UI",Inter,ui-sans-serif,sans-serif' in stylesheet
    assert 'font-size:27px' in stylesheet
    assert 'letter-spacing:-.012em' in stylesheet
    assert 'font-weight:600' in stylesheet


def test_theme_script_defaults_to_light_and_persists_explicit_dark_choice(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/login/app.js", headers={}),
        now=_NOW,
    )

    assert response.status is HTTPStatus.OK
    assert dict(response.headers)["Content-Type"] == "text/javascript; charset=utf-8"
    script = response.body.decode("utf-8")
    assert "ilaios-theme" in script
    assert "storedTheme()==='dark'?'dark':'light'" in script
    assert "localStorage.setItem('ilaios-theme',value)" in script
    assert "dark?'#0A0A0A':'#FFFFFF'" in script
    assert "#0B0E13" not in script
    assert "fetch('/auth/providers'" in script


def test_login_assets_reject_query_parameters_and_non_get_methods(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    query = runtime.dispatch(
        RuntimeRequest(method="GET", target="/?next=/li", headers={}),
        now=_NOW,
    )
    post = runtime.dispatch(
        RuntimeRequest(method="POST", target="/", headers={}),
        now=_NOW,
    )

    assert query.status is HTTPStatus.BAD_REQUEST
    assert query.body == b'{"error":"unexpected query parameters"}'
    assert post.status is HTTPStatus.METHOD_NOT_ALLOWED
    assert dict(post.headers)["Allow"] == "GET"


def test_login_runtime_delegates_existing_google_oauth_start(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    response = runtime.dispatch(
        RuntimeRequest(method="GET", target="/auth/google/start", headers={}),
        now=_NOW,
    )

    assert response.status is HTTPStatus.FOUND
    assert dict(response.headers)["Location"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    assert _CALLBACK in dict(response.headers)["Location"]
