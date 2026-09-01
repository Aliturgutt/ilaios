from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from services.desktop_oidc import OIDCProviderConfig
from services.desktop_oidc_windows import DesktopOIDCService

NOW = datetime(2026, 8, 16, 16, 0, tzinfo=timezone.utc)


def _microsoft_provider() -> OIDCProviderConfig:
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
        scopes=("openid", "profile", "email"),
    )


def _google_provider() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="google",
        display_name="Google",
        issuer="https://accounts.example.test",
        authorization_endpoint="https://accounts.example.test/authorize",
        token_endpoint="https://accounts.example.test/token",
        jwks_uri="https://accounts.example.test/jwks",
        client_id="google-desktop-client",
    )


def test_microsoft_uses_stable_localhost_path_with_ephemeral_port() -> None:
    service = DesktopOIDCService((_microsoft_provider(),), credential_store=None)

    started = service.start(
        "microsoft",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )
    query = parse_qs(urlparse(started.authorization_url).query)

    assert query["redirect_uri"] == ["http://localhost:43123/oauth/callback"]
    flow = service._flows[started.state]
    assert flow.redirect_uri == "http://localhost:43123/oauth/callback"


def test_google_keeps_proven_ipv4_loopback_redirect() -> None:
    service = DesktopOIDCService((_google_provider(),), credential_store=None)

    started = service.start(
        "google",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )
    query = parse_qs(urlparse(started.authorization_url).query)

    assert query["redirect_uri"] == ["http://127.0.0.1:43123/oauth/callback"]
