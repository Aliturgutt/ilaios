"""Sign in with Apple OIDC configuration and canonical identity bridge."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from services.central_identity import CentralIdentityError, IdentityProvider, VerifiedExternalIdentity
from services.identity import VerifiedOIDCClaims

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_AUTHORIZATION_ENDPOINT = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_ENDPOINT = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_ENDPOINT = "https://appleid.apple.com/auth/revoke"
APPLE_JWKS_URI = "https://appleid.apple.com/auth/keys"


class AppleOIDCConfigurationError(ValueError):
    """Sign in with Apple production configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class AppleOIDCEnvironment:
    production_services_id: str
    development_services_id: str
    native_client_id: str
    team_id: str
    key_id: str
    production_web_redirects: tuple[str, ...]

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> AppleOIDCEnvironment:
        production_services_id = _required(env, "ILAIOS_APPLE_PRODUCTION_SERVICES_ID")
        development_services_id = _required(env, "ILAIOS_APPLE_DEVELOPMENT_SERVICES_ID")
        native_client_id = _required(env, "ILAIOS_APPLE_NATIVE_CLIENT_ID")
        team_id = _required(env, "ILAIOS_APPLE_TEAM_ID")
        key_id = _required(env, "ILAIOS_APPLE_KEY_ID")
        if production_services_id == development_services_id:
            raise AppleOIDCConfigurationError(
                "Apple production and development Services IDs must be distinct"
            )
        raw_redirects = _required(env, "ILAIOS_APPLE_PRODUCTION_WEB_REDIRECTS")
        redirects = tuple(value.strip() for value in raw_redirects.split(",") if value.strip())
        if not redirects:
            raise AppleOIDCConfigurationError(
                "Apple production redirect allowlist must not be empty"
            )
        for redirect in redirects:
            _validate_production_redirect(redirect)
        if len(set(redirects)) != len(redirects):
            raise AppleOIDCConfigurationError(
                "Apple production redirect allowlist contains duplicates"
            )
        return cls(
            production_services_id=production_services_id,
            development_services_id=development_services_id,
            native_client_id=native_client_id,
            team_id=team_id,
            key_id=key_id,
            production_web_redirects=redirects,
        )

    def require_production_web_redirect(self, redirect_uri: str) -> str:
        redirect = redirect_uri.strip()
        if redirect not in self.production_web_redirects:
            raise AppleOIDCConfigurationError(
                "Apple production redirect URI is not allowlisted"
            )
        return redirect

    def authorization_parameters(
        self, *, redirect_uri: str, state: str, nonce: str
    ) -> dict[str, str]:
        redirect = self.require_production_web_redirect(redirect_uri)
        normalized_state = state.strip()
        normalized_nonce = nonce.strip()
        if not normalized_state or not normalized_nonce:
            raise AppleOIDCConfigurationError("Apple state and nonce are required")
        return {
            "client_id": self.production_services_id,
            "redirect_uri": redirect,
            "response_type": "code id_token",
            "response_mode": "form_post",
            "scope": "name email",
            "state": normalized_state,
            "nonce": normalized_nonce,
        }


def verified_apple_identity(claims: VerifiedOIDCClaims) -> VerifiedExternalIdentity:
    """Convert cryptographically verified Apple claims to canonical identity input."""
    if claims.issuer != APPLE_ISSUER:
        raise CentralIdentityError("Apple identity issuer mismatch")
    subject = claims.subject.strip()
    if not subject:
        raise CentralIdentityError("Apple identity subject is required")

    attributes = {key: value for key, value in claims.attributes}
    email = attributes.get("email", "").strip().casefold() or None
    email_verified = attributes.get("email_verified", "").strip().casefold() == "true"
    if not email_verified:
        email = None

    return VerifiedExternalIdentity(
        provider=IdentityProvider.APPLE,
        subject=subject,
        email=email,
        email_verified=email is not None,
        issuer=APPLE_ISSUER,
    ).normalized()


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise AppleOIDCConfigurationError(f"{key} is required")
    return value


def _validate_production_redirect(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AppleOIDCConfigurationError("Apple production redirect URI must use HTTPS")
    if parsed.username or parsed.password or parsed.fragment:
        raise AppleOIDCConfigurationError(
            "Apple production redirect URI contains forbidden components"
        )
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise AppleOIDCConfigurationError(
            "Apple production redirect URI must not use a loopback host"
        )
