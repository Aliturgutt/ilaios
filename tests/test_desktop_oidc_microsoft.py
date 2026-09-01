from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import cast
from urllib.parse import parse_qs, urlparse

import jwt
import pytest

import services.desktop_oidc_microsoft as microsoft
import services.desktop_oidc_threaded as threaded
from services.desktop_oidc import DesktopIdentityError, OIDCProviderConfig
from services.identity import IdentityKind, VerifiedOIDCClaims

NOW = datetime(2026, 8, 16, 16, 0, tzinfo=timezone.utc)
TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"


def _provider(*, client_secret: str | None = None) -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="microsoft",
        display_name="Microsoft",
        issuer="https://login.microsoftonline.com/{tenantid}/v2.0",
        authorization_endpoint=(
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        ),
        token_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys",
        client_id="00001111-aaaa-2222-bbbb-3333cccc4444",
        client_secret=client_secret,
        scopes=("openid", "profile", "email"),
    )


class _Response:
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict[str, str]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _HTTP:
    def __init__(self) -> None:
        self.posts: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _Response:
        self.posts.append({"url": url, **kwargs})
        data = kwargs.get("data")
        if isinstance(data, dict) and data.get("grant_type") == "refresh_token":
            return _Response(
                {
                    "id_token": "microsoft-refreshed-id-token",
                    "refresh_token": "rotated-microsoft-refresh-token",
                }
            )
        return _Response(
            {
                "id_token": "microsoft-signed-id-token",
                "refresh_token": "microsoft-refresh-token",
            }
        )


class _Store:
    def __init__(self) -> None:
        self.record: threaded._StoredRefreshCredential | None = None
        self.clear_count = 0

    def load(self) -> threaded._StoredRefreshCredential | None:
        return self.record

    def save(self, provider_id: str, refresh_token: str) -> None:
        self.record = threaded._StoredRefreshCredential(provider_id, refresh_token)

    def clear(self) -> None:
        self.record = None
        self.clear_count += 1


class _Verifier:
    def __init__(
        self,
        provider: OIDCProviderConfig,
        *,
        expected_nonce: str | None,
    ) -> None:
        self.provider = provider
        self.expected_nonce = expected_nonce
        self.verified_expires_at = NOW + timedelta(minutes=45)
        self.display_identity = "user@outlook.com"

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token in {
            "microsoft-signed-id-token",
            "microsoft-refreshed-id-token",
        }
        return VerifiedOIDCClaims(
            issuer=ISSUER,
            audience=self.provider.client_id,
            subject="microsoft-user-123",
            tenant_id="desktop-test-tenant",
            expires_at=self.verified_expires_at,
            issued_at=NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset(),
            authentication_methods=frozenset({"pwd"}),
        )


class _JwksClient:
    def __init__(self, key_issuer: str) -> None:
        self.key_issuer = key_issuer

    def fetch_data(self) -> dict[str, object]:
        return {
            "keys": [
                {
                    "kid": "key-1",
                    "issuer": self.key_issuer,
                }
            ]
        }


class _SigningKey:
    key = object()


class _VerifierJwksClient:
    def __init__(self, uri: str) -> None:
        self.uri = uri

    def get_signing_key_from_jwt(self, encoded_token: str) -> _SigningKey:
        return _SigningKey()

    def fetch_data(self) -> dict[str, object]:
        return {
            "keys": [
                {
                    "kid": "key-1",
                    "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0",
                }
            ]
        }


def _claims(*, issuer: str = ISSUER, tid: str = TENANT) -> dict[str, object]:
    return {
        "iss": issuer,
        "tid": tid,
        "sub": "user-123",
        "aud": _provider().client_id,
        "iat": NOW.timestamp(),
        "exp": (NOW + timedelta(minutes=45)).timestamp(),
        "nonce": "nonce-1",
    }


def test_microsoft_authorization_requests_offline_access_and_pkce() -> None:
    service = microsoft.DesktopOIDCService((_provider(),), credential_store=_Store())

    started = service.start(
        "microsoft", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )
    query = parse_qs(urlparse(started.authorization_url).query)

    assert "offline_access" in query["scope"][0].split()
    assert query["code_challenge_method"] == ["S256"]
    assert "client_secret" not in query


def test_microsoft_public_client_configuration_rejects_secret() -> None:
    with pytest.raises(
        DesktopIdentityError,
        match="public client without a secret",
    ):
        microsoft.DesktopOIDCService(
            (_provider(client_secret="must-not-be-used"),),
            credential_store=_Store(),
        )


def test_microsoft_tenant_template_binds_tid_to_issuer() -> None:
    assert microsoft._validated_microsoft_issuer(_provider(), _claims()) == ISSUER

    with pytest.raises(DesktopIdentityError, match="tenant/issuer binding"):
        microsoft._validated_microsoft_issuer(
            _provider(),
            _claims(
                issuer="https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000/v2.0"
            ),
        )

    with pytest.raises(DesktopIdentityError, match="tid claim must be a GUID"):
        microsoft._validated_microsoft_issuer(
            _provider(),
            _claims(tid="not-a-guid"),
        )


def test_microsoft_signing_key_issuer_is_bound_to_token_tenant() -> None:
    microsoft._validate_microsoft_signing_key_issuer(
        cast(
            jwt.PyJWKClient,
            _JwksClient("https://login.microsoftonline.com/{tenantid}/v2.0"),
        ),
        "key-1",
        _claims(),
        ISSUER,
    )

    with pytest.raises(DesktopIdentityError, match="signing-key issuer binding"):
        microsoft._validate_microsoft_signing_key_issuer(
            cast(
                jwt.PyJWKClient,
                _JwksClient(
                    "https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000/v2.0"
                ),
            ),
            "key-1",
            _claims(),
            ISSUER,
        )


def test_microsoft_interactive_verifier_rejects_nonce_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = _claims()
    claims["nonce"] = "wrong-nonce"
    monkeypatch.setattr(
        jwt,
        "get_unverified_header",
        lambda token: {"alg": "RS256", "kid": "key-1"},
    )
    monkeypatch.setattr(jwt, "PyJWKClient", _VerifierJwksClient)
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *args, **kwargs: claims,
    )

    verifier = microsoft._MicrosoftOIDCTokenVerifier(
        _provider(), expected_nonce="expected-nonce"
    )
    with pytest.raises(DesktopIdentityError, match="nonce validation failed"):
        verifier.verify("signed-token")


def test_microsoft_verifier_passes_client_id_as_audience_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_audience: list[object] = []

    def reject_audience(*args: object, **kwargs: object) -> dict[str, object]:
        observed_audience.append(kwargs.get("audience"))
        raise jwt.InvalidAudienceError("audience mismatch")

    monkeypatch.setattr(
        jwt,
        "get_unverified_header",
        lambda token: {"alg": "RS256", "kid": "key-1"},
    )
    monkeypatch.setattr(jwt, "PyJWKClient", _VerifierJwksClient)
    monkeypatch.setattr(jwt, "decode", reject_audience)

    verifier = microsoft._MicrosoftOIDCTokenVerifier(
        _provider(), expected_nonce="nonce-1"
    )
    with pytest.raises(DesktopIdentityError, match="ID token verification failed"):
        verifier.verify("signed-token")
    assert observed_audience == [_provider().client_id]


def test_successful_microsoft_callback_persists_refresh_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    http = _HTTP()
    monkeypatch.setattr(
        microsoft,
        "_trusted_microsoft_issuer_for_token",
        lambda provider, token: ISSUER,
    )
    monkeypatch.setattr(
        microsoft,
        "_MicrosoftOIDCTokenVerifier",
        _Verifier,
    )
    service = microsoft.DesktopOIDCService(
        (_provider(),),
        request_session=http,
        credential_store=store,
    )
    started = service.start(
        "microsoft", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )

    result = service.complete(started.state, "authorization-code", now=NOW)

    assert result.status == "authenticated"
    assert result.provider_id == "microsoft"
    assert result.display_identity == "user@outlook.com"
    assert store.record is not None
    assert store.record.provider_id == "microsoft"
    assert store.record.refresh_token == "microsoft-refresh-token"


def test_microsoft_restore_rotates_refresh_and_logout_clears_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    store.save("microsoft", "microsoft-refresh-token")
    http = _HTTP()
    monkeypatch.setattr(
        microsoft,
        "_trusted_microsoft_issuer_for_token",
        lambda provider, token: ISSUER,
    )
    monkeypatch.setattr(
        microsoft,
        "_MicrosoftOIDCTokenVerifier",
        _Verifier,
    )
    service = microsoft.DesktopOIDCService(
        (_provider(),),
        request_session=http,
        credential_store=store,
    )

    restored = service.status("__ilaios_restore__", now=NOW)

    assert restored.status == "authenticated"
    assert restored.provider_id == "microsoft"
    assert restored.display_identity == "user@outlook.com"
    assert restored.session_id is not None
    assert store.record is not None
    assert store.record.refresh_token == "rotated-microsoft-refresh-token"

    service.logout(restored.session_id)
    assert store.record is None
    assert store.clear_count == 1
