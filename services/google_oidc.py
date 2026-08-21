"""Google OIDC configuration and canonical identity bridge.

This module contains only provider-specific Google configuration/claim handling.
It reuses the existing provider-neutral Desktop OIDC and central identity
boundaries. Google email is metadata only; the immutable Google ``sub`` claim is
the external identity key.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from services.central_identity import (
    CentralIdentityError,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.desktop_oidc import OIDCProviderConfig
from services.identity import VerifiedOIDCClaims

GOOGLE_ISSUER = "https://accounts.google.com"
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"


class GoogleOIDCConfigurationError(ValueError):
    """Google production OAuth configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class GoogleOIDCEnvironment:
    production_web_client_id: str
    development_web_client_id: str
    desktop_client_id: str
    production_web_redirects: tuple[str, ...]

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> GoogleOIDCEnvironment:
        production_web_client_id = _required(
            env, "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID"
        )
        development_web_client_id = _required(
            env, "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID"
        )
        desktop_client_id = _required(env, "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID")
        if production_web_client_id == development_web_client_id:
            raise GoogleOIDCConfigurationError(
                "Google production and development web clients must be distinct"
            )
        raw_redirects = _required(env, "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS")
        redirects = tuple(
            value.strip() for value in raw_redirects.split(",") if value.strip()
        )
        if not redirects:
            raise GoogleOIDCConfigurationError(
                "Google production redirect allowlist must not be empty"
            )
        for redirect in redirects:
            _validate_production_redirect(redirect)
        if len(set(redirects)) != len(redirects):
            raise GoogleOIDCConfigurationError(
                "Google production redirect allowlist contains duplicates"
            )
        return cls(
            production_web_client_id=production_web_client_id,
            development_web_client_id=development_web_client_id,
            desktop_client_id=desktop_client_id,
            production_web_redirects=redirects,
        )

    def desktop_provider(self) -> OIDCProviderConfig:
        return OIDCProviderConfig(
            provider_id="google",
            display_name="Google",
            issuer=GOOGLE_ISSUER,
            authorization_endpoint=GOOGLE_AUTHORIZATION_ENDPOINT,
            token_endpoint=GOOGLE_TOKEN_ENDPOINT,
            jwks_uri=GOOGLE_JWKS_URI,
            client_id=self.desktop_client_id,
        )

    def require_production_web_redirect(self, redirect_uri: str) -> str:
        redirect = redirect_uri.strip()
        if redirect not in self.production_web_redirects:
            raise GoogleOIDCConfigurationError(
                "Google production redirect URI is not allowlisted"
            )
        return redirect


def verified_google_identity(claims: VerifiedOIDCClaims) -> VerifiedExternalIdentity:
    """Convert cryptographically verified Google OIDC claims to canonical input."""

    if claims.issuer != GOOGLE_ISSUER:
        raise CentralIdentityError("Google identity issuer mismatch")
    subject = claims.subject.strip()
    if not subject:
        raise CentralIdentityError("Google identity subject is required")

    verified_email: str | None = None
    for key, value in claims.attributes:
        if key == "verified_email" and value.strip():
            verified_email = value.strip().casefold()
            break

    return VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject=subject,
        email=verified_email,
        email_verified=verified_email is not None,
        issuer=GOOGLE_ISSUER,
    ).normalized()


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise GoogleOIDCConfigurationError(f"{key} is required")
    return value


def _validate_production_redirect(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise GoogleOIDCConfigurationError(
            "Google production redirect URI must use HTTPS"
        )
    if parsed.username or parsed.password or parsed.fragment:
        raise GoogleOIDCConfigurationError(
            "Google production redirect URI contains forbidden components"
        )
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise GoogleOIDCConfigurationError(
            "Google production redirect URI must not use a loopback host"
        )
