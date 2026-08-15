from __future__ import annotations

import json

import pytest

from services.desktop_oidc import DesktopIdentityError
from services.desktop_oidc_client_auth import desktop_oidc_service_from_environment


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"id_token": "unused"}


class _HTTP:
    def __init__(self) -> None:
        self.posts: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _Response:
        self.posts.append({"url": url, **kwargs})
        return _Response()


def _provider_document(**extra: object) -> str:
    provider: dict[str, object] = {
        "provider_id": "google",
        "display_name": "Google",
        "issuer": "https://accounts.google.com",
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        "client_id": "desktop-client-id",
        "scopes": ["openid", "profile", "email"],
    }
    provider.update(extra)
    return json.dumps([provider])


def test_empty_environment_keeps_identity_disabled() -> None:
    assert desktop_oidc_service_from_environment({}) is None


def test_embedded_client_secret_is_rejected() -> None:
    environment = {
        "ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": _provider_document(
            client_secret="must-not-live-in-provider-json"
        )
    }
    with pytest.raises(DesktopIdentityError, match="must not be embedded"):
        desktop_oidc_service_from_environment(environment)


def test_referenced_client_secret_must_exist() -> None:
    environment = {
        "ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": _provider_document(
            client_secret_env="ILAIOS_GOOGLE_OIDC_CLIENT_SECRET"
        )
    }
    with pytest.raises(DesktopIdentityError, match="environment variable is missing"):
        desktop_oidc_service_from_environment(environment)


def test_client_secret_is_injected_only_for_matching_token_request() -> None:
    delegate = _HTTP()
    environment = {
        "ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON": _provider_document(
            client_secret_env="ILAIOS_GOOGLE_OIDC_CLIENT_SECRET"
        ),
        "ILAIOS_GOOGLE_OIDC_CLIENT_SECRET": "local-google-secret",
    }
    service = desktop_oidc_service_from_environment(
        environment,
        request_session=delegate,
    )
    assert service is not None
    assert service.providers() == (
        {"provider_id": "google", "display_name": "Google"},
    )
    assert "local-google-secret" not in repr(service.providers())

    http = getattr(service, "_http")
    http.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": "desktop-client-id", "code": "authorization-code"},
    )
    http.post(
        "https://example.test/token",
        data={"client_id": "desktop-client-id", "code": "authorization-code"},
    )

    first = delegate.posts[0]["data"]
    second = delegate.posts[1]["data"]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    assert first["client_secret"] == "local-google-secret"
    assert "client_secret" not in second
