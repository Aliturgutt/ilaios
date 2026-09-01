from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from services.desktop_oidc import (
    DesktopIdentityError,
    DesktopOIDCService,
    OIDCProviderConfig,
)
from services.identity import IdentityKind, VerifiedOIDCClaims


NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


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
    def __init__(self) -> None:
        self.payload = {"id_token": "signed-id-token"}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return self.payload


class _HTTP:
    def __init__(self) -> None:
        self.posts: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> _Response:
        self.posts.append({"url": url, **kwargs})
        return _Response()


class _IssuingHTTP(_HTTP):
    def __init__(self) -> None:
        super().__init__()
        self.issued_at: datetime | None = None

    def post(self, url: str, **kwargs: object) -> _Response:
        # Model a provider that creates the ID token during the network exchange,
        # after the Desktop callback request has already arrived.
        time.sleep(0.01)
        self.issued_at = datetime.now(timezone.utc)
        return super().post(url, **kwargs)


class _Verifier:
    def __init__(self, provider: OIDCProviderConfig, nonce: str) -> None:
        self.provider = provider
        self.nonce = nonce
        self.verified_expires_at = NOW + timedelta(minutes=30)

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "signed-id-token"
        return VerifiedOIDCClaims(
            issuer=self.provider.issuer,
            audience=self.provider.client_id,
            subject="user-123",
            tenant_id="tenant-123",
            expires_at=self.verified_expires_at,
            issued_at=NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset({("verified_email", "user@example.test")}),
            authentication_methods=frozenset({"pwd", "mfa"}),
        )


class _FreshTokenVerifier:
    def __init__(
        self,
        provider: OIDCProviderConfig,
        nonce: str,
        http: _IssuingHTTP,
    ) -> None:
        self.provider = provider
        self.nonce = nonce
        self.http = http
        self.verified_expires_at: datetime | None = None

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "signed-id-token"
        issued_at = self.http.issued_at
        assert issued_at is not None
        self.verified_expires_at = issued_at + timedelta(minutes=30)
        return VerifiedOIDCClaims(
            issuer=self.provider.issuer,
            audience=self.provider.client_id,
            subject="fresh-user",
            tenant_id="fresh-tenant",
            expires_at=self.verified_expires_at,
            issued_at=issued_at,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset(),
            authentication_methods=frozenset({"pwd"}),
        )


def test_empty_environment_keeps_external_account_sign_in_disabled() -> None:
    assert DesktopOIDCService.from_environment({}) is None


def test_provider_configuration_requires_https_authority() -> None:
    bad = _provider()
    bad = OIDCProviderConfig(
        provider_id=bad.provider_id,
        display_name=bad.display_name,
        issuer="http://accounts.example.test",
        authorization_endpoint=bad.authorization_endpoint,
        token_endpoint=bad.token_endpoint,
        jwks_uri=bad.jwks_uri,
        client_id=bad.client_id,
    )
    with pytest.raises(DesktopIdentityError, match="HTTPS"):
        DesktopOIDCService((bad,))


def test_authorization_start_uses_state_nonce_and_s256_pkce() -> None:
    service = DesktopOIDCService((_provider(),))
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )
    parsed = urlparse(started.authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["desktop-client-id"]
    assert query["state"] == [started.state]
    assert len(query["nonce"][0]) >= 32
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) >= 43
    assert query["redirect_uri"] == ["http://127.0.0.1:43123/oauth/callback"]


def test_verified_federation_issues_session_no_longer_than_id_token() -> None:
    http = _HTTP()
    verifiers: list[_Verifier] = []

    def verifier_factory(provider: OIDCProviderConfig, nonce: str) -> _Verifier:
        verifier = _Verifier(provider, nonce)
        verifiers.append(verifier)
        return verifier

    service = DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=verifier_factory,
    )
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )
    result = service.complete(started.state, "authorization-code", now=NOW)

    assert result.status == "authenticated"
    assert result.provider_id == "google"
    assert result.principal_id == "user-123"
    assert result.tenant_id == "tenant-123"
    assert result.display_identity == "user@example.test"
    assert result.session_id is not None
    session = service.validate_session(result.session_id, now=NOW + timedelta(minutes=29))
    assert session.principal_id == "user-123"
    with pytest.raises(DesktopIdentityError, match="invalid or expired"):
        service.validate_session(result.session_id, now=NOW + timedelta(minutes=31))

    assert verifiers
    post = http.posts[0]
    assert post["url"] == "https://accounts.example.test/token"
    data = post["data"]
    assert isinstance(data, dict)
    assert data["grant_type"] == "authorization_code"
    assert data["code"] == "authorization-code"
    assert isinstance(data["code_verifier"], str)
    assert len(data["code_verifier"]) >= 43


def test_live_completion_uses_post_exchange_time_for_fresh_id_token() -> None:
    http = _IssuingHTTP()
    service = DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _FreshTokenVerifier(
            provider, nonce, http
        ),
    )
    started = service.start("google", "http://127.0.0.1:43123/oauth/callback")

    result = service.complete(started.state, "authorization-code")

    assert http.issued_at is not None
    assert result.status == "authenticated"
    assert result.principal_id == "fresh-user"
    assert result.session_id is not None


def test_state_is_single_use_and_logout_removes_cached_session_result() -> None:
    http = _HTTP()
    service = DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _Verifier(provider, nonce),
    )
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )
    result = service.complete(started.state, "authorization-code", now=NOW)
    assert result.session_id is not None

    with pytest.raises(DesktopIdentityError, match="invalid or expired"):
        service.complete(started.state, "authorization-code", now=NOW)

    service.logout(result.session_id)
    with pytest.raises(DesktopIdentityError, match="unknown or expired"):
        service.status(started.state, now=NOW)
    with pytest.raises(DesktopIdentityError, match="unknown"):
        service.validate_session(result.session_id, now=NOW)
