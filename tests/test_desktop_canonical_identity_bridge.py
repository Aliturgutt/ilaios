from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import jwt
import pytest
import requests

import services.google_oidc as google_oidc
from services.central_identity import IdentityProvider
from services.desktop_oidc import DesktopIdentityError, OIDCProviderConfig
from services.desktop_oidc_windows import DesktopOIDCService
from services.google_oidc import verify_google_desktop_id_token
from services.identity import IdentityKind, Principal

_NOW = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)


class _SigningKey:
    key = object()


class _JwksClient:
    def __init__(self, uri: str) -> None:
        assert uri == google_oidc.GOOGLE_JWKS_URI

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        assert token == "signed.desktop.token"
        return _SigningKey()


def test_google_desktop_token_verifier_binds_google_subject_and_desktop_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        jwt,
        "get_unverified_header",
        lambda _token: {"alg": "RS256"},
    )
    monkeypatch.setattr(jwt, "PyJWKClient", _JwksClient)

    observed: dict[str, object] = {}

    def decode(
        token: str,
        key: object,
        *,
        algorithms: list[str],
        audience: str,
        issuer: str,
        options: dict[str, object],
    ) -> dict[str, object]:
        observed.update(
            {
                "token": token,
                "key": key,
                "algorithms": algorithms,
                "audience": audience,
                "issuer": issuer,
                "options": options,
            }
        )
        return {
            "iss": google_oidc.GOOGLE_ISSUER,
            "aud": "desktop-client-id",
            "sub": "google-subject-123",
            "iat": int((_NOW - timedelta(minutes=1)).timestamp()),
            "exp": int((_NOW + timedelta(minutes=59)).timestamp()),
            "email": "Owner@Example.COM",
            "email_verified": True,
        }

    monkeypatch.setattr(jwt, "decode", decode)

    identity = verify_google_desktop_id_token(
        "signed.desktop.token",
        client_id="desktop-client-id",
        now=_NOW,
    )

    assert identity.provider is IdentityProvider.GOOGLE
    assert identity.subject == "google-subject-123"
    assert identity.email == "owner@example.com"
    assert identity.email_verified is True
    assert observed["audience"] == "desktop-client-id"
    assert observed["issuer"] == google_oidc.GOOGLE_ISSUER
    assert observed["algorithms"] == ["RS256"]


class _CanonicalResponse:
    status_code = 200

    def json(self) -> dict[str, str]:
        return {
            "user_id": "usr_canonical123",
            "tenant_id": "tnt_canonical123",
        }


class _CanonicalHTTP:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _CanonicalResponse:
        self.calls.append({"url": url, **kwargs})
        return _CanonicalResponse()


def _google_provider() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="google",
        display_name="Google",
        issuer=google_oidc.GOOGLE_ISSUER,
        authorization_endpoint=google_oidc.GOOGLE_AUTHORIZATION_ENDPOINT,
        token_endpoint=google_oidc.GOOGLE_TOKEN_ENDPOINT,
        jwks_uri=google_oidc.GOOGLE_JWKS_URI,
        client_id="desktop-client-id",
    )


def test_windows_desktop_replaces_local_subject_with_canonical_coordinates() -> None:
    http = _CanonicalHTTP()
    service = DesktopOIDCService(
        (_google_provider(),),
        canonical_request_session=cast(requests.Session, http),
    )
    local = Principal(
        principal_id="raw-google-subject",
        tenant_id="desktop-derived-tenant",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset({("verified_email", "owner@example.com")}),
        authentication_methods=frozenset(),
    )

    resolved = service._canonicalize_principal(
        "google",
        "signed.desktop.token",
        local,
        _NOW,
    )

    assert resolved.principal_id == "usr_canonical123"
    assert resolved.tenant_id == "tnt_canonical123"
    assert resolved.roles == local.roles
    assert resolved.attributes == local.attributes
    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://app.ilaios.com/auth/desktop/canonicalize"
    assert call["json"] == {
        "provider_id": "google",
        "id_token": "signed.desktop.token",
    }


def test_windows_desktop_fails_closed_for_noncanonical_provider() -> None:
    service = DesktopOIDCService(
        (_google_provider(),),
        canonical_request_session=cast(requests.Session, _CanonicalHTTP()),
    )
    local = Principal(
        principal_id="raw-subject",
        tenant_id="desktop-derived-tenant",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset(),
        authentication_methods=frozenset(),
    )

    with pytest.raises(DesktopIdentityError):
        service._canonicalize_principal(
            "microsoft",
            "signed.desktop.token",
            local,
            _NOW,
        )
