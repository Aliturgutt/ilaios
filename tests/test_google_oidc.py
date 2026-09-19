from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.central_identity import CentralIdentityError, IdentityProvider
from services.google_oidc import (
    GOOGLE_AUTHORIZATION_ENDPOINT,
    GOOGLE_ISSUER,
    GOOGLE_JWKS_URI,
    GOOGLE_TOKEN_ENDPOINT,
    GoogleOIDCConfigurationError,
    GoogleOIDCEnvironment,
    verified_google_identity,
)
from services.identity import IdentityKind, VerifiedOIDCClaims

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def _environment() -> dict[str, str]:
    return {
        "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID": "prod-web.apps.googleusercontent.com",
        "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID": "dev-web.apps.googleusercontent.com",
        "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID": "desktop.apps.googleusercontent.com",
        "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS": (
            "https://app.ilaios.com/auth/google/callback,"
            "https://ilaios.com/auth/google/callback"
        ),
    }


def _claims(*, issuer: str = GOOGLE_ISSUER) -> VerifiedOIDCClaims:
    return VerifiedOIDCClaims(
        issuer=issuer,
        audience="prod-web.apps.googleusercontent.com",
        subject="google-sub-123",
        tenant_id="provider-derived-not-canonical",
        expires_at=NOW + timedelta(minutes=30),
        issued_at=NOW - timedelta(minutes=1),
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset({("verified_email", "User@Example.com")}),
        authentication_methods=frozenset({"pwd"}),
    )


def test_google_environment_requires_distinct_dev_and_prod_clients() -> None:
    env = _environment()
    env["ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID"] = env[
        "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID"
    ]

    with pytest.raises(GoogleOIDCConfigurationError, match="must be distinct"):
        GoogleOIDCEnvironment.from_environment(env)


def test_google_production_redirect_allowlist_rejects_loopback_and_http() -> None:
    for redirect in (
        "http://app.ilaios.com/auth/google/callback",
        "https://127.0.0.1/auth/google/callback",
    ):
        env = _environment()
        env["ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS"] = redirect
        with pytest.raises(GoogleOIDCConfigurationError):
            GoogleOIDCEnvironment.from_environment(env)


def test_google_desktop_provider_uses_pinned_google_authority() -> None:
    config = GoogleOIDCEnvironment.from_environment(_environment())
    provider = config.desktop_provider()

    assert provider.provider_id == "google"
    assert provider.issuer == GOOGLE_ISSUER
    assert provider.authorization_endpoint == GOOGLE_AUTHORIZATION_ENDPOINT
    assert provider.token_endpoint == GOOGLE_TOKEN_ENDPOINT
    assert provider.jwks_uri == GOOGLE_JWKS_URI
    assert provider.client_id == "desktop.apps.googleusercontent.com"
    assert provider.client_secret is None


def test_google_production_redirect_must_be_exactly_allowlisted() -> None:
    config = GoogleOIDCEnvironment.from_environment(_environment())
    allowed = "https://app.ilaios.com/auth/google/callback"

    assert config.require_production_web_redirect(allowed) == allowed
    with pytest.raises(GoogleOIDCConfigurationError, match="not allowlisted"):
        config.require_production_web_redirect(
            "https://app.ilaios.com/auth/google/callback/extra"
        )


def test_verified_google_subject_becomes_external_identity_not_email_key() -> None:
    identity = verified_google_identity(_claims())

    assert identity.provider is IdentityProvider.GOOGLE
    assert identity.subject == "google-sub-123"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.key() == (IdentityProvider.GOOGLE, "", "google-sub-123")


def test_verified_google_identity_rejects_wrong_issuer() -> None:
    with pytest.raises(CentralIdentityError, match="issuer mismatch"):
        verified_google_identity(_claims(issuer="https://attacker.example"))
