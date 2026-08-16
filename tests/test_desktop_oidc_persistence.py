from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

import services.desktop_oidc_threaded as threaded
from services.desktop_oidc import OIDCProviderConfig
from services.identity import IdentityKind, VerifiedOIDCClaims

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


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
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload

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
            return _Response({"id_token": "refreshed-id-token"})
        return _Response(
            {
                "id_token": "signed-id-token",
                "refresh_token": "offline-refresh-token",
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
    def __init__(self, provider: OIDCProviderConfig, nonce: str | None = None) -> None:
        self.provider = provider
        self.nonce = nonce
        self.verified_expires_at = NOW + timedelta(minutes=45)

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token in {"signed-id-token", "refreshed-id-token"}
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
            authentication_methods=frozenset({"pwd"}),
        )


def test_google_authorization_requests_offline_refresh_credential() -> None:
    service = threaded.DesktopOIDCService((_provider(),), credential_store=_Store())

    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )
    query = parse_qs(urlparse(started.authorization_url).query)

    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["include_granted_scopes"] == ["true"]
    assert query["code_challenge_method"] == ["S256"]


def test_successful_google_callback_persists_refresh_credential() -> None:
    store = _Store()
    http = _HTTP()
    service = threaded.DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _Verifier(provider, nonce),
        credential_store=store,
    )
    started = service.start(
        "google", "http://127.0.0.1:43123/oauth/callback", now=NOW
    )

    result = service.complete(started.state, "authorization-code", now=NOW)

    assert result.status == "authenticated"
    assert store.record is not None
    assert store.record.provider_id == "google"
    assert store.record.refresh_token == "offline-refresh-token"


def test_reserved_restore_state_refreshes_and_reissues_local_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _Store()
    store.save("google", "offline-refresh-token")
    http = _HTTP()
    monkeypatch.setattr(
        threaded,
        "_RefreshOIDCTokenVerifier",
        lambda provider: _Verifier(provider),
    )
    service = threaded.DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        credential_store=store,
    )

    restored = service.status("__ilaios_restore__", now=NOW)

    assert restored.status == "authenticated"
    assert restored.provider_id == "google"
    assert restored.principal_id == "user-123"
    assert restored.tenant_id == "tenant-123"
    assert restored.display_identity == "user@example.test"
    assert restored.session_id is not None
    refresh_post = http.posts[-1]
    data = refresh_post["data"]
    assert isinstance(data, dict)
    assert data["grant_type"] == "refresh_token"
    assert data["refresh_token"] == "offline-refresh-token"

    service.logout(restored.session_id)
    assert store.record is None
    assert store.clear_count == 1


def test_restore_without_persistent_credential_remains_signed_out() -> None:
    service = threaded.DesktopOIDCService(
        (_provider(),),
        credential_store=_Store(),
    )

    restored = service.status("__ilaios_restore__", now=NOW)

    assert restored.status == "pending"
    assert restored.session_id is None
