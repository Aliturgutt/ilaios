"""Google OIDC configuration and canonical identity bridge."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final
from urllib.parse import urlparse

import jwt

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


class GoogleDesktopIdentityVerificationError(CentralIdentityError):
    """Google Desktop ID token could not be verified for canonicalization."""


_ALLOWED_GOOGLE_DESKTOP_ALGORITHMS: Final = frozenset({"RS256"})
_MAX_GOOGLE_DESKTOP_TOKEN_LIFETIME: Final = timedelta(hours=2)


@dataclass(frozen=True, slots=True)
class GoogleOIDCEnvironment:
    production_web_client_id: str
    development_web_client_id: str
    desktop_client_id: str
    production_web_redirects: tuple[str, ...]

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> GoogleOIDCEnvironment:
        production_web_client_id = _required(env, "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_ID")
        development_web_client_id = _required(env, "ILAIOS_GOOGLE_DEVELOPMENT_WEB_CLIENT_ID")
        desktop_client_id = _required(env, "ILAIOS_GOOGLE_DESKTOP_CLIENT_ID")
        if production_web_client_id == development_web_client_id:
            raise GoogleOIDCConfigurationError(
                "Google production and development web clients must be distinct"
            )
        raw_redirects = _required(env, "ILAIOS_GOOGLE_PRODUCTION_WEB_REDIRECTS")
        redirects = tuple(value.strip() for value in raw_redirects.split(",") if value.strip())
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


def verify_google_desktop_id_token(
    encoded_token: str,
    *,
    client_id: str,
    now: datetime,
) -> VerifiedExternalIdentity:
    """Verify a Desktop Google ID token before canonical account resolution.

    The native Desktop broker already validates nonce/PKCE locally. This server-side
    verification independently binds the same provider token to Google's issuer,
    the registered Desktop client audience, signature, and bounded temporal claims.
    The token is never persisted or returned.
    """

    token = encoded_token.strip()
    audience = client_id.strip()
    if token != encoded_token or not token or len(token) > 16_384:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop token is invalid"
        )
    if not audience:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop client identity is unavailable"
        )
    if now.tzinfo is None or now.utcoffset() is None:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop verification time is invalid"
        )
    current = now.astimezone(UTC)

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if (
            not isinstance(algorithm, str)
            or algorithm not in _ALLOWED_GOOGLE_DESKTOP_ALGORITHMS
        ):
            raise GoogleDesktopIdentityVerificationError(
                "Google Desktop signing algorithm is not allowed"
            )
        key = jwt.PyJWKClient(GOOGLE_JWKS_URI).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=[algorithm],
            audience=audience,
            issuer=GOOGLE_ISSUER,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub"],
                "verify_exp": False,
                "verify_iat": False,
            },
        )
    except GoogleDesktopIdentityVerificationError:
        raise
    except Exception as error:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop ID token verification failed"
        ) from error

    issued_at = _claim_datetime(claims, "iat")
    expires_at = _claim_datetime(claims, "exp")
    if issued_at > current or expires_at <= current:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop token is not currently valid"
        )
    if expires_at - issued_at > _MAX_GOOGLE_DESKTOP_TOKEN_LIFETIME:
        raise GoogleDesktopIdentityVerificationError(
            "Google Desktop token lifetime exceeds policy"
        )

    subject = _claim_string(claims, "sub")
    email_value = claims.get("email")
    verified_email = (
        email_value.strip().casefold()
        if isinstance(email_value, str)
        and email_value.strip()
        and claims.get("email_verified") is True
        else None
    )
    return VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject=subject,
        email=verified_email,
        email_verified=verified_email is not None,
        issuer=GOOGLE_ISSUER,
    ).normalized()


def _claim_string(claims: Mapping[str, Any], name: str) -> str:
    value = claims.get(name)
    if not isinstance(value, str) or not value.strip():
        raise GoogleDesktopIdentityVerificationError(
            f"Google Desktop {name} claim is invalid"
        )
    return value.strip()


def _claim_datetime(claims: Mapping[str, Any], name: str) -> datetime:
    value = claims.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GoogleDesktopIdentityVerificationError(
            f"Google Desktop {name} claim is invalid"
        )
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise GoogleDesktopIdentityVerificationError(
            f"Google Desktop {name} claim is invalid"
        ) from error


def verified_google_identity(claims: VerifiedOIDCClaims) -> VerifiedExternalIdentity:
    """Convert verified Google claims to canonical identity input."""
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
        raise GoogleOIDCConfigurationError("Google production redirect URI must use HTTPS")
    if parsed.username or parsed.password or parsed.fragment:
        raise GoogleOIDCConfigurationError(
            "Google production redirect URI contains forbidden components"
        )
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise GoogleOIDCConfigurationError(
            "Google production redirect URI must not use a loopback host"
        )
