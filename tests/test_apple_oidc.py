from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.apple_oidc import (
    APPLE_AUTHORIZATION_ENDPOINT,
    APPLE_ISSUER,
    APPLE_JWKS_URI,
    APPLE_REVOKE_ENDPOINT,
    APPLE_TOKEN_ENDPOINT,
    AppleOIDCConfigurationError,
    AppleOIDCEnvironment,
    verified_apple_identity,
)
from services.central_identity import CentralIdentityError, IdentityProvider
from services.identity import IdentityKind, VerifiedOIDCClaims

NOW = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)


def _environment() -> dict[str, str]:
    return {
        "ILAIOS_APPLE_PRODUCTION_SERVICES_ID": "com.ilaios.web",
        "ILAIOS_APPLE_DEVELOPMENT_SERVICES_ID": "com.ilaios.web.dev",
        "ILAIOS_APPLE_NATIVE_CLIENT_ID": "com.ilaios.app",
        "ILAIOS_APPLE_TEAM_ID": "TEAM123456",
        "ILAIOS_APPLE_KEY_ID": "KEY1234567",
        "ILAIOS_APPLE_PRODUCTION_WEB_REDIRECTS": (
            "https://app.ilaios.com/auth/apple/callback,"
            "https://ilaios.com/auth/apple/callback"
        ),
    }


def _claims(
    *,
    issuer: str = APPLE_ISSUER,
    subject: str = "apple-stable-subject-123",
    email: str = "relay@privaterelay.appleid.com",
    email_verified: str = "true",
) -> VerifiedOIDCClaims:
    return VerifiedOIDCClaims(
        issuer=issuer,
        audience="com.ilaios.web",
        subject=subject,
        tenant_id="provider-derived-not-canonical",
        expires_at=NOW + timedelta(minutes=30),
        issued_at=NOW - timedelta(minutes=1),
        kind=IdentityKind.HUMAN,
        roles=frozenset({"user"}),
        attributes=frozenset({("email", email), ("email_verified", email_verified)}),
        authentication_methods=frozenset({"apple"}),
    )


def test_apple_endpoints_are_pinned_to_apple_authority() -> None:
    assert APPLE_ISSUER == "https://appleid.apple.com"
    assert APPLE_AUTHORIZATION_ENDPOINT == "https://appleid.apple.com/auth/authorize"
    assert APPLE_TOKEN_ENDPOINT == "https://appleid.apple.com/auth/token"
    assert APPLE_REVOKE_ENDPOINT == "https://appleid.apple.com/auth/revoke"
    assert APPLE_JWKS_URI == "https://appleid.apple.com/auth/keys"


def test_apple_environment_requires_distinct_dev_and_prod_services_ids() -> None:
    env = _environment()
    env["ILAIOS_APPLE_DEVELOPMENT_SERVICES_ID"] = env[
        "ILAIOS_APPLE_PRODUCTION_SERVICES_ID"
    ]
    with pytest.raises(AppleOIDCConfigurationError, match="must be distinct"):
        AppleOIDCEnvironment.from_environment(env)


def test_apple_production_redirect_rejects_http_loopback_and_fragments() -> None:
    for redirect in (
        "http://app.ilaios.com/auth/apple/callback",
        "https://127.0.0.1/auth/apple/callback",
        "https://app.ilaios.com/auth/apple/callback#fragment",
    ):
        env = _environment()
        env["ILAIOS_APPLE_PRODUCTION_WEB_REDIRECTS"] = redirect
        with pytest.raises(AppleOIDCConfigurationError):
            AppleOIDCEnvironment.from_environment(env)


def test_apple_authorization_requires_exact_redirect_state_and_nonce() -> None:
    config = AppleOIDCEnvironment.from_environment(_environment())
    redirect = "https://app.ilaios.com/auth/apple/callback"
    params = config.authorization_parameters(
        redirect_uri=redirect,
        state="state-123",
        nonce="nonce-123",
    )
    assert params == {
        "client_id": "com.ilaios.web",
        "redirect_uri": redirect,
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "name email",
        "state": "state-123",
        "nonce": "nonce-123",
    }
    with pytest.raises(AppleOIDCConfigurationError, match="state and nonce"):
        config.authorization_parameters(
            redirect_uri=redirect,
            state="",
            nonce="nonce-123",
        )
    with pytest.raises(AppleOIDCConfigurationError, match="not allowlisted"):
        config.authorization_parameters(
            redirect_uri="https://attacker.example/callback",
            state="state-123",
            nonce="nonce-123",
        )


def test_apple_stable_subject_is_identity_key_and_relay_email_is_metadata() -> None:
    identity = verified_apple_identity(_claims())
    assert identity.provider is IdentityProvider.APPLE
    assert identity.subject == "apple-stable-subject-123"
    assert identity.email == "relay@privaterelay.appleid.com"
    assert identity.email_verified is True
    assert identity.key() == (IdentityProvider.APPLE, "", "apple-stable-subject-123")


def test_apple_relay_email_change_does_not_change_identity_key() -> None:
    first = verified_apple_identity(_claims(email="first@privaterelay.appleid.com"))
    second = verified_apple_identity(_claims(email="second@privaterelay.appleid.com"))
    assert first.key() == second.key()
    assert first.email != second.email


def test_apple_unverified_email_is_not_promoted_to_verified_metadata() -> None:
    identity = verified_apple_identity(_claims(email_verified="false"))
    assert identity.email is None
    assert identity.email_verified is False


def test_verified_apple_identity_rejects_wrong_issuer_and_blank_subject() -> None:
    with pytest.raises(CentralIdentityError, match="issuer mismatch"):
        verified_apple_identity(_claims(issuer="https://attacker.example"))
    with pytest.raises(CentralIdentityError, match="subject is required"):
        verified_apple_identity(_claims(subject="   "))
