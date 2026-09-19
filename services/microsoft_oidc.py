"""Microsoft OIDC configuration and canonical identity bridge.

Supports a single Microsoft identity provider for personal Microsoft accounts and
organizational Microsoft Entra ID accounts. Provider credentials are verified
outside this module before claims are converted into canonical identity input.
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

MICROSOFT_AUTHORIZATION_ENDPOINT = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
)
MICROSOFT_TOKEN_ENDPOINT = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
)
MICROSOFT_JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
MICROSOFT_ISSUER_PREFIX = "https://login.microsoftonline.com/"
MICROSOFT_ISSUER_SUFFIX = "/v2.0"
MICROSOFT_CONSUMER_TENANT_ID = "9188040d-6c67-4c5b-b112-36a304b66dad"


class MicrosoftOIDCConfigurationError(ValueError):
    """Microsoft production OAuth configuration is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class MicrosoftOIDCEnvironment:
    production_web_client_id: str
    development_web_client_id: str
    desktop_client_id: str
    production_web_redirects: tuple[str, ...]

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> MicrosoftOIDCEnvironment:
        production_web_client_id = _required(
            env, "ILAIOS_MICROSOFT_PRODUCTION_WEB_CLIENT_ID"
        )
        development_web_client_id = _required(
            env, "ILAIOS_MICROSOFT_DEVELOPMENT_WEB_CLIENT_ID"
        )
        desktop_client_id = _required(env, "ILAIOS_MICROSOFT_DESKTOP_CLIENT_ID")
        if production_web_client_id == development_web_client_id:
            raise MicrosoftOIDCConfigurationError(
                "Microsoft production and development web clients must be distinct"
            )
        raw_redirects = _required(
            env, "ILAIOS_MICROSOFT_PRODUCTION_WEB_REDIRECTS"
        )
        redirects = tuple(
            value.strip() for value in raw_redirects.split(",") if value.strip()
        )
        if not redirects:
            raise MicrosoftOIDCConfigurationError(
                "Microsoft production redirect allowlist must not be empty"
            )
        for redirect in redirects:
            _validate_production_redirect(redirect)
        if len(set(redirects)) != len(redirects):
            raise MicrosoftOIDCConfigurationError(
                "Microsoft production redirect allowlist contains duplicates"
            )
        return cls(
            production_web_client_id=production_web_client_id,
            development_web_client_id=development_web_client_id,
            desktop_client_id=desktop_client_id,
            production_web_redirects=redirects,
        )

    def desktop_provider(self) -> OIDCProviderConfig:
        return OIDCProviderConfig(
            provider_id="microsoft",
            display_name="Microsoft",
            issuer="https://login.microsoftonline.com/common/v2.0",
            authorization_endpoint=MICROSOFT_AUTHORIZATION_ENDPOINT,
            token_endpoint=MICROSOFT_TOKEN_ENDPOINT,
            jwks_uri=MICROSOFT_JWKS_URI,
            client_id=self.desktop_client_id,
        )

    def require_production_web_redirect(self, redirect_uri: str) -> str:
        redirect = redirect_uri.strip()
        if redirect not in self.production_web_redirects:
            raise MicrosoftOIDCConfigurationError(
                "Microsoft production redirect URI is not allowlisted"
            )
        return redirect


def verified_microsoft_identity(
    claims: VerifiedOIDCClaims,
) -> VerifiedExternalIdentity:
    issuer = _validated_token_issuer(claims.issuer)
    subject = claims.subject.strip()
    if not subject:
        raise CentralIdentityError("Microsoft identity subject is required")

    verified_email: str | None = None
    for key, value in claims.attributes:
        if key in {"verified_email", "preferred_username", "email"} and value.strip():
            verified_email = value.strip().casefold()
            break

    return VerifiedExternalIdentity(
        provider=IdentityProvider.MICROSOFT,
        subject=subject,
        email=verified_email,
        email_verified=verified_email is not None,
        issuer=issuer,
    ).normalized()


def _validated_token_issuer(value: str) -> str:
    issuer = value.strip()
    if not issuer.startswith(MICROSOFT_ISSUER_PREFIX) or not issuer.endswith(
        MICROSOFT_ISSUER_SUFFIX
    ):
        raise CentralIdentityError("Microsoft identity issuer mismatch")
    tenant_id = issuer[
        len(MICROSOFT_ISSUER_PREFIX) : -len(MICROSOFT_ISSUER_SUFFIX)
    ]
    if (
        not tenant_id
        or "/" in tenant_id
        or tenant_id in {"common", "organizations", "consumers"}
    ):
        raise CentralIdentityError(
            "Microsoft token issuer must contain a concrete tenant"
        )
    return issuer


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise MicrosoftOIDCConfigurationError(f"{key} is required")
    return value


def _validate_production_redirect(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise MicrosoftOIDCConfigurationError(
            "Microsoft production redirect URI must use HTTPS"
        )
    if parsed.username or parsed.password or parsed.fragment:
        raise MicrosoftOIDCConfigurationError(
            "Microsoft production redirect URI contains forbidden components"
        )
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise MicrosoftOIDCConfigurationError(
            "Microsoft production redirect URI must not use a loopback host"
        )
