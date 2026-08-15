from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from services.desktop_oidc import (
    DesktopIdentityError,
    DesktopOIDCService,
    OIDCProviderConfig,
)


NOW = datetime(2026, 8, 15, 17, 5, tzinfo=timezone.utc)


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


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def json(self) -> object:
        return self.payload

    def raise_for_status(self) -> None:
        response = requests.Response()
        response.status_code = 400
        raise requests.HTTPError(response=response)


class _HTTP:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def post(self, url: str, **kwargs: object) -> _Response:
        return _Response(self.payload)


def _start(service: DesktopOIDCService) -> str:
    return service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    ).state


def test_provider_error_code_is_casefolded_and_bounded() -> None:
    service = DesktopOIDCService(
        (_provider(),),
        request_session=_HTTP({"error": " INVALID_CLIENT "}),  # type: ignore[arg-type]
    )

    with pytest.raises(
        DesktopIdentityError,
        match=r"^OIDC token exchange failed: invalid_client$",
    ):
        service.complete(_start(service), "authorization-code", now=NOW)


def test_non_object_provider_payload_does_not_leak_content() -> None:
    service = DesktopOIDCService(
        (_provider(),),
        request_session=_HTTP("SECRET-TOKEN"),  # type: ignore[arg-type]
    )

    with pytest.raises(
        DesktopIdentityError,
        match=r"^OIDC token exchange failed$",
    ) as captured:
        service.complete(_start(service), "authorization-code", now=NOW)

    assert "SECRET-TOKEN" not in str(captured.value)
