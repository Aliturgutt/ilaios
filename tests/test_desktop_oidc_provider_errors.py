from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from services.desktop_oidc import (
    DesktopIdentityError,
    DesktopOIDCService,
    OIDCProviderConfig,
)


NOW = datetime(2026, 8, 15, 17, 0, tzinfo=timezone.utc)


def _provider() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="google",
        display_name="Google",
        issuer="https://accounts.example.test",
        authorization_endpoint="https://accounts.example.test/authorize",
        token_endpoint="https://accounts.example.test/token",
        jwks_uri="https://accounts.example.test/jwks",
        client_id="desktop-client-id",
    )


class _ProviderErrorResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        response = requests.Response()
        response.status_code = 400
        raise requests.HTTPError(response=response)


class _ProviderErrorHTTP:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def post(self, url: str, **kwargs: object) -> _ProviderErrorResponse:
        return _ProviderErrorResponse(self._payload)


def test_token_exchange_surfaces_only_normalized_provider_error_code() -> None:
    service = DesktopOIDCService(
        (_provider(),),
        request_session=_ProviderErrorHTTP(
            {
                "error": "invalid_grant",
                "error_description": "authorization code SECRET-CODE was rejected",
                "access_token": "SECRET-TOKEN",
            }
        ),  # type: ignore[arg-type]
    )
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )

    with pytest.raises(
        DesktopIdentityError,
        match=r"^OIDC token exchange failed: invalid_grant$",
    ) as captured:
        service.complete(started.state, "authorization-code", now=NOW)

    message = str(captured.value)
    assert "SECRET-CODE" not in message
    assert "SECRET-TOKEN" not in message
    assert "error_description" not in message


def test_token_exchange_rejects_unsafe_provider_error_text() -> None:
    service = DesktopOIDCService(
        (_provider(),),
        request_session=_ProviderErrorHTTP(
            {"error": "invalid grant access_token=SECRET-TOKEN"}
        ),  # type: ignore[arg-type]
    )
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )

    with pytest.raises(
        DesktopIdentityError,
        match=r"^OIDC token exchange failed$",
    ) as captured:
        service.complete(started.state, "authorization-code", now=NOW)

    assert "SECRET-TOKEN" not in str(captured.value)
