from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService


NOW = datetime(2026, 8, 15, 17, 30, tzinfo=timezone.utc)


class _Response:
    def json(self) -> object:
        return {"error": "invalid_grant"}

    def raise_for_status(self) -> None:
        response = requests.Response()
        response.status_code = 400
        raise requests.HTTPError(response=response)


class _CaptureHTTP:
    def __init__(self) -> None:
        self.data: object | None = None

    def post(self, url: str, **kwargs: object) -> _Response:
        self.data = kwargs.get("data")
        return _Response()


def _environment(*, client_secret: str | None = None) -> dict[str, str]:
    secret_field = (
        f',\n                "client_secret": "{client_secret}"'
        if client_secret is not None
        else ""
    )
    return {
        "ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": f"""
        [
          {{
            "provider_id": "google",
            "display_name": "Google",
            "issuer": "https://accounts.google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "client_id": "desktop-client.apps.googleusercontent.com"{secret_field},
            "scopes": ["openid", "profile", "email"]
          }}
        ]
        """
    }


def test_google_desktop_provider_environment_loads_without_client_secret() -> None:
    service = DesktopOIDCService.from_environment(_environment())

    assert service is not None
    assert service.providers() == (
        {"provider_id": "google", "display_name": "Google"},
    )


def test_google_desktop_provider_forwards_configured_client_secret() -> None:
    service = DesktopOIDCService.from_environment(
        _environment(client_secret="test-client-secret")
    )
    assert service is not None

    capture = _CaptureHTTP()
    setattr(service, "_http", capture)

    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )

    with pytest.raises(
        DesktopIdentityError,
        match=r"^OIDC token exchange failed: invalid_grant$",
    ):
        service.complete(started.state, "authorization-code", now=NOW)

    assert isinstance(capture.data, dict)
    assert capture.data["client_id"] == "desktop-client.apps.googleusercontent.com"
    assert capture.data["client_secret"] == "test-client-secret"
    assert capture.data["code_verifier"]
