from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import services.desktop_oidc_threaded as threaded
from services.desktop_oidc import OIDCProviderConfig
from services.identity import IdentityKind, VerifiedOIDCClaims

NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)


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
    def post(self, url: str, **kwargs: object) -> _Response:
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


def test_google_logout_clears_persistent_credential_and_restart_stays_signed_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    session = service.complete(started.state, "authorization-code", now=NOW)
    assert session.session_id is not None
    assert store.record is not None

    service.logout(session.session_id)

    assert store.record is None
    assert store.clear_count == 1

    monkeypatch.setattr(
        threaded,
        "_RefreshOIDCTokenVerifier",
        lambda provider: _Verifier(provider),
    )
    restarted = threaded.DesktopOIDCService(
        (_provider(),),
        request_session=http,
        credential_store=store,
    )
    restored = restarted.status("__ilaios_restore__", now=NOW)

    assert restored.status == "pending"
    assert restored.session_id is None
