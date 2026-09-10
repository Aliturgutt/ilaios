from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from apps.web_app_runtime.login_server import LoginAppRuntime
from apps.web_app_runtime.server import RuntimeRequest

_NOW = datetime(2026, 9, 10, tzinfo=UTC)


def _runtime(database: Path) -> LoginAppRuntime:
    runtime = LoginAppRuntime.from_environment(
        {
            "ILAIOS_APP_ENV": "development",
            "ILAIOS_IDENTITY_DATABASE_PATH": str(database),
            "ILAIOS_SESSION_SIGNING_KEY": "test-signing-key",
            "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID": "prod.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID": "dev.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID": "desktop.apps.googleusercontent.com",
            "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS": (
                "https://app.ilaios.com/auth/google/callback"
            ),
            "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_SECRET": "server-only-client-secret",
            "ILAIOS_GOOGLE_WEB_OAUTH_STATE_SECRET": (
                "state-secret-material-that-is-distinct-and-long-enough"
            ),
        }
    )
    assert isinstance(runtime, LoginAppRuntime)
    return runtime


def test_login_language_selector_is_visible_and_switches_locale(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path / "identity.db")

    turkish = runtime.dispatch(RuntimeRequest(method="GET", target="/", headers={}), now=_NOW)
    english = runtime.dispatch(
        RuntimeRequest(method="GET", target="/?lang=en", headers={}), now=_NOW
    )

    tr_document = turkish.body.decode("utf-8")
    en_document = english.body.decode("utf-8")

    assert 'aria-label="Dil"' in tr_document
    assert 'href="/?lang=tr"' in tr_document
    assert 'href="/?lang=en"' in tr_document
    assert 'hreflang="tr"' in tr_document
    assert 'hreflang="en"' in tr_document
    assert '>TR</a>' in tr_document
    assert '>EN</a>' in tr_document
    assert '<html lang="tr"' in tr_document
    assert '<html lang="en"' in en_document
    assert 'aria-label="Language"' in en_document
    assert 'href="/?lang=tr"' in en_document
    assert 'href="/?lang=en"' in en_document

    assert 'class="theme-toggle"' in tr_document
    assert 'id="theme-toggle"' in tr_document
    assert '<span aria-hidden="true">◐</span>' in tr_document
    assert '<strong>Tema</strong>' in tr_document
    assert 'aria-label="Temayı değiştir"' in tr_document
    assert '<strong>Theme</strong>' in en_document
    assert 'aria-label="Toggle theme"' in en_document
    assert 'id="theme-light"' not in tr_document
    assert 'id="theme-dark"' not in tr_document
