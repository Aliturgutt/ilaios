from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.central_identity import CentralIdentityError, IdentityProvider
from services.identity import IdentityKind, VerifiedOIDCClaims
from services.microsoft_oidc import (
    MICROSOFT_AUTHORIZATION_ENDPOINT,
    MICROSOFT_CONSUMER_TENANT_ID,
    MICROSOFT_JWKS_URI,
    MICROSOFT_TOKEN_ENDPOINT,
    MicrosoftOIDCConfigurationError,
    MicrosoftOIDCEnvironment,
    verified_microsoft_identity,
)

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
ORG_TENANT = "11111111-2222-3333-4444-555555555555"
ORG_ISSUER = f"https://login.microsoftonline.com/{ORG_TENANT}/v2.0"
CONSUMER_ISSUER = f"https://login.microsoftonline.com/{MICROSOFT_CONSUMER_TENANT_ID}/v2.0"


def _environment() -> dict[str, str]:
    return {
        "ILAIOS_MICROSOFT_PRODUCTION_WEB_CLIENT_ID": "prod-ms-client",
        "ILAIOS_MICROSOFT_DEVELOPMENT_WEB_CLIENT_ID": "dev-ms-client",
        "ILAIOS_MICROSOFT_DESKTOP_CLIENT_ID": "desktop-ms-client",
        "ILAIOS_MICROSOFT_PRODUCTION_WEB_REDIRECTS": "https://app.ilaios.com/auth/microsoft/callback,https://ilaios.com/auth/microsoft/callback",
    }


def _claims(*, issuer: str, subject: str = "microsoft-sub-123") -> VerifiedOIDCClaims:
    return VerifiedOIDCClaims(
        issuer=issuer,
        audience="prod-ms-client",
        subject=subject,
        tenant_id="provider-derived-not-canonical",
        expires_at=NOW + timedelta(minutes=30),
        issued_at=NOW - timedelta(minutes=1),
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset({("preferred_username", "User@Example.com")}),
        authentication_methods=frozenset({"pwd"}),
    )


def test_microsoft_environment_requires_distinct_dev_and_prod_clients() -> None:
    env = _environment()
    env["ILAIOS_MICROSOFT_DEVELOPMENT_WEB_CLIENT_ID"] = env["ILAIOS_MICROSOFT_PRODUCTION_WEB_CLIENT_ID"]
    with pytest.raises(MicrosoftOIDCConfigurationError, match="must be distinct"):
        MicrosoftOIDCEnvironment.from_environment(env)


def test_microsoft_production_redirect_allowlist_rejects_loopback_and_http() -> None:
    for redirect in ("http://app.ilaios.com/auth/microsoft/callback", "https://127.0.0.1/auth/microsoft/callback"):
        env = _environment()
        env["ILAIOS_MICROSOFT_PRODUCTION_WEB_REDIRECTS"] = redirect
        with pytest.raises(MicrosoftOIDCConfigurationError):
            MicrosoftOIDCEnvironment.from_environment(env)


def test_microsoft_desktop_provider_uses_common_authority_without_secret() -> None:
    provider = MicrosoftOIDCEnvironment.from_environment(_environment()).desktop_provider()
    assert provider.provider_id == "microsoft"
    assert provider.authorization_endpoint == MICROSOFT_AUTHORIZATION_ENDPOINT
    assert provider.token_endpoint == MICROSOFT_TOKEN_ENDPOINT
    assert provider.jwks_uri == MICROSOFT_JWKS_URI
    assert provider.client_id == "desktop-ms-client"
    assert provider.client_secret is None


def test_microsoft_accepts_personal_and_organizational_concrete_issuers() -> None:
    personal = verified_microsoft_identity(_claims(issuer=CONSUMER_ISSUER))
    organization = verified_microsoft_identity(_claims(issuer=ORG_ISSUER))
    assert personal.provider is IdentityProvider.MICROSOFT
    assert personal.issuer == CONSUMER_ISSUER
    assert organization.issuer == ORG_ISSUER
    assert personal.email == "user@example.com"


def test_microsoft_identity_key_is_namespaced_by_verified_issuer() -> None:
    personal = verified_microsoft_identity(_claims(issuer=CONSUMER_ISSUER, subject="same-sub"))
    organization = verified_microsoft_identity(_claims(issuer=ORG_ISSUER, subject="same-sub"))
    assert personal.key() != organization.key()
    assert personal.key() == (IdentityProvider.MICROSOFT, CONSUMER_ISSUER, "same-sub")


def test_microsoft_rejects_generic_or_attacker_issuer() -> None:
    for issuer in (
        "https://login.microsoftonline.com/common/v2.0",
        "https://login.microsoftonline.com/organizations/v2.0",
        "https://attacker.example/tenant/v2.0",
    ):
        with pytest.raises(CentralIdentityError):
            verified_microsoft_identity(_claims(issuer=issuer))


def test_microsoft_production_redirect_must_be_exactly_allowlisted() -> None:
    config = MicrosoftOIDCEnvironment.from_environment(_environment())
    allowed = "https://app.ilaios.com/auth/microsoft/callback"
    assert config.require_production_web_redirect(allowed) == allowed
    with pytest.raises(MicrosoftOIDCConfigurationError, match="not allowlisted"):
        config.require_production_web_redirect(f"{allowed}/extra")
