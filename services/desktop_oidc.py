"""Provider-neutral OIDC Authorization Code + PKCE broker for ILAIOS Desktop.

External identity is converted into the canonical ``services.identity``
principal/session model only after cryptographic OIDC verification. Raw IdP
credentials remain adapter-owned and are never returned to the Flutter client.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from urllib.parse import urlencode, urlparse

import requests

from services.identity import (
    AuthenticationBoundary,
    IdentityKind,
    IdentityPolicy,
    OIDCTokenVerifier,
    Principal,
    Session,
    SessionRegistry,
    VerifiedOIDCClaims,
)

_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_PROVIDER_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_ALLOWED_ALGORITHMS = frozenset({"RS256", "PS256", "ES256"})
_FLOW_LIFETIME = timedelta(minutes=5)
_SESSION_LIFETIME = timedelta(hours=8)
VerifierFactory = Callable[["OIDCProviderConfig", str], OIDCTokenVerifier]


class DesktopIdentityError(PermissionError):
    """Desktop federation/session boundary rejected the request."""


@dataclass(frozen=True, slots=True)
class OIDCProviderConfig:
    provider_id: str
    display_name: str
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    client_id: str
    client_secret: str | None = None
    scopes: tuple[str, ...] = ("openid", "profile", "email")


@dataclass(frozen=True, slots=True)
class DesktopAuthStart:
    provider_id: str
    state: str
    authorization_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class DesktopAuthStatus:
    state: str
    status: str
    provider_id: str
    session_id: str | None = None
    principal_id: str | None = None
    tenant_id: str | None = None
    display_identity: str | None = None
    li_founder: bool = False


@dataclass(frozen=True, slots=True)
class _AuthFlow:
    provider_id: str
    state: str
    nonce: str
    code_verifier: str
    redirect_uri: str
    expires_at: datetime


class DesktopOIDCService:
    """Issue short-lived Desktop sessions after verified OIDC federation."""

    def __init__(
        self,
        providers: tuple[OIDCProviderConfig, ...],
        *,
        request_session: requests.Session | None = None,
        verifier_factory: VerifierFactory | None = None,
    ) -> None:
        if len({item.provider_id for item in providers}) != len(providers):
            raise DesktopIdentityError("duplicate Desktop identity provider")
        self._providers = {
            item.provider_id: _validate_provider(item) for item in providers
        }
        self._flows: dict[str, _AuthFlow] = {}
        self._results: dict[str, DesktopAuthStatus] = {}
        self._session_tenants: dict[str, str] = {}
        self._session_li_founder: dict[str, bool] = {}
        self._session_identity_credentials: dict[str, tuple[str, str]] = {}
        self._session_registry = SessionRegistry(_SESSION_LIFETIME)
        self._http = request_session or requests.Session()
        self._verifier_factory = verifier_factory or (
            lambda provider, nonce: _PyJwtOIDCTokenVerifier(
                provider, expected_nonce=nonce
            )
        )

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> DesktopOIDCService | None:
        env = environment or os.environ
        raw = env.get("ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON", "").strip()
        if not raw:
            return None
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as error:
            raise DesktopIdentityError("Desktop OIDC provider JSON is invalid") from error
        if not isinstance(document, list):
            raise DesktopIdentityError(
                "Desktop OIDC provider configuration must be a list"
            )
        providers: list[OIDCProviderConfig] = []
        for item in document:
            if not isinstance(item, dict):
                raise DesktopIdentityError("Desktop OIDC provider must be an object")
            provider = cast(dict[str, Any], item)
            scopes = provider.get("scopes", ["openid", "profile", "email"])
            if not isinstance(scopes, list) or not all(
                isinstance(value, str) and value.strip() for value in scopes
            ):
                raise DesktopIdentityError(
                    "Desktop OIDC scopes must be non-empty strings"
                )
            providers.append(
                OIDCProviderConfig(
                    provider_id=_required_text(provider, "provider_id"),
                    display_name=_required_text(provider, "display_name"),
                    issuer=_required_text(provider, "issuer"),
                    authorization_endpoint=_required_text(
                        provider, "authorization_endpoint"
                    ),
                    token_endpoint=_required_text(provider, "token_endpoint"),
                    jwks_uri=_required_text(provider, "jwks_uri"),
                    client_id=_required_text(provider, "client_id"),
                    client_secret=_optional_text(provider, "client_secret"),
                    scopes=tuple(cast(list[str], scopes)),
                )
            )
        if not providers:
            raise DesktopIdentityError("Desktop OIDC provider list must not be empty")
        return cls(tuple(providers))

    def providers(self) -> tuple[dict[str, str], ...]:
        return tuple(
            {
                "provider_id": provider.provider_id,
                "display_name": provider.display_name,
            }
            for provider in sorted(
                self._providers.values(), key=lambda item: item.provider_id
            )
        )

    def start(
        self,
        provider_id: str,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> DesktopAuthStart:
        current = _utc(now)
        self._purge(current)
        provider = self._providers.get(provider_id)
        if provider is None:
            raise DesktopIdentityError("unknown Desktop identity provider")
        _validate_loopback_redirect(redirect_uri)

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        challenge = _base64url(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        )
        expires_at = current + _FLOW_LIFETIME
        self._flows[state] = _AuthFlow(
            provider_id=provider.provider_id,
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            expires_at=expires_at,
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": provider.client_id,
                "redirect_uri": redirect_uri,
                "scope": " ".join(provider.scopes),
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return DesktopAuthStart(
            provider_id=provider.provider_id,
            state=state,
            authorization_url=f"{provider.authorization_endpoint}?{query}",
            expires_at=expires_at,
        )

    def complete(
        self,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        callback_time = _utc(now)
        self._purge(callback_time)
        flow = self._flows.pop(state, None)
        if flow is None or flow.expires_at <= callback_time:
            raise DesktopIdentityError("Desktop OIDC state is invalid or expired")
        if not code or not code.strip():
            raise DesktopIdentityError("OIDC authorization code is required")
        provider = self._providers[flow.provider_id]

        token_data = {
            "grant_type": "authorization_code",
            "client_id": provider.client_id,
            "code": code.strip(),
            "redirect_uri": flow.redirect_uri,
            "code_verifier": flow.code_verifier,
        }
        if provider.client_secret is not None:
            token_data["client_secret"] = provider.client_secret

        try:
            response = self._http.post(
                provider.token_endpoint,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise DesktopIdentityError("OIDC token exchange failed") from error

        try:
            payload = response.json()
        except ValueError as error:
            try:
                response.raise_for_status()
            except requests.RequestException as status_error:
                raise DesktopIdentityError("OIDC token exchange failed") from status_error
            raise DesktopIdentityError("OIDC token response is malformed") from error

        try:
            response.raise_for_status()
        except requests.RequestException as error:
            provider_error = _safe_provider_error_code(payload)
            detail = f": {provider_error}" if provider_error is not None else ""
            raise DesktopIdentityError(
                f"OIDC token exchange failed{detail}"
            ) from error

        if not isinstance(payload, dict):
            raise DesktopIdentityError("OIDC token response is malformed")
        encoded_token = payload.get("id_token")
        if not isinstance(encoded_token, str) or not encoded_token:
            raise DesktopIdentityError(
                "OIDC token response did not contain an ID token"
            )

        # A provider can issue the ID token during the network exchange above.
        # Re-sample wall-clock time before validating iat/exp and issuing the
        # local session; the callback-arrival timestamp can already be stale.
        current = _utc(now)
        verifier = self._verifier_factory(provider, flow.nonce)
        principal = AuthenticationBoundary(
            verifier,
            IdentityPolicy(
                trusted_issuers=frozenset({provider.issuer}),
                audience=provider.client_id,
                maximum_session=_SESSION_LIFETIME,
            ),
        ).authenticate(encoded_token, current)
        principal = self._canonicalize_principal(
            provider.provider_id,
            encoded_token,
            principal,
            current,
        )
        verified_expiry = getattr(verifier, "verified_expires_at", None)
        if not isinstance(verified_expiry, datetime):
            raise DesktopIdentityError(
                "OIDC verifier did not bind the local session to token expiry"
            )
        remaining = verified_expiry.astimezone(timezone.utc) - current
        lifetime = min(_SESSION_LIFETIME, remaining)
        if lifetime <= timedelta(0):
            raise DesktopIdentityError("verified OIDC token is already expired")

        session_id = secrets.token_urlsafe(32)
        session = self._session_registry.issue(
            session_id,
            principal,
            current,
            lifetime,
        )
        self._session_tenants[session.session_id] = session.tenant_id
        self._bind_session_entitlements(session.session_id, principal)
        self._bind_session_identity_credential(
            session.session_id,
            provider.provider_id,
            encoded_token,
        )
        result = DesktopAuthStatus(
            state=state,
            status="authenticated",
            provider_id=provider.provider_id,
            session_id=session.session_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            display_identity=_verified_email(principal),
            li_founder=self._session_li_founder.get(session.session_id, False),
        )
        self._results[state] = result
        return result

    def reject(self, state: str, reason: str, now: datetime | None = None) -> None:
        current = _utc(now)
        self._purge(current)
        flow = self._flows.pop(state, None)
        if flow is None:
            raise DesktopIdentityError("Desktop OIDC state is invalid or expired")
        safe_reason = reason.strip()[:120] or "identity provider rejected sign-in"
        self._results[state] = DesktopAuthStatus(
            state=state,
            status=f"rejected:{safe_reason}",
            provider_id=flow.provider_id,
        )

    def status(
        self,
        state: str,
        now: datetime | None = None,
    ) -> DesktopAuthStatus:
        current = _utc(now)
        self._purge(current)
        result = self._results.get(state)
        if result is not None:
            return result
        flow = self._flows.get(state)
        if flow is None:
            raise DesktopIdentityError("Desktop OIDC state is unknown or expired")
        return DesktopAuthStatus(
            state=state,
            status="pending",
            provider_id=flow.provider_id,
        )

    def _canonicalize_principal(
        self,
        provider_id: str,
        encoded_token: str,
        principal: Principal,
        now: datetime,
    ) -> Principal:
        """Provider-specific composition hook; base broker keeps verified claims unchanged."""
        return principal

    def validate_session(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> Session:
        current = _utc(now)
        tenant_id = self._session_tenants.get(session_id)
        if tenant_id is None:
            raise DesktopIdentityError("Desktop session is unknown")
        try:
            return self._session_registry.validate(session_id, tenant_id, current)
        except PermissionError as error:
            self._session_tenants.pop(session_id, None)
            self._session_li_founder.pop(session_id, None)
            self._session_identity_credentials.pop(session_id, None)
            raise DesktopIdentityError(
                "Desktop session is invalid or expired"
            ) from error

    def is_li_founder_session(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> bool:
        self.validate_session(session_id, now)
        return self._session_li_founder.get(session_id, False)

    def _bind_session_entitlements(
        self,
        session_id: str,
        principal: Principal,
    ) -> None:
        self._session_li_founder[session_id] = (
            ("ilaios_li_founder", "true") in principal.attributes
        )

    def _bind_session_identity_credential(
        self,
        session_id: str,
        provider_id: str,
        encoded_token: str,
    ) -> None:
        normalized_provider = provider_id.strip()
        normalized_token = encoded_token.strip()
        if not normalized_provider or not normalized_token:
            raise DesktopIdentityError("Desktop identity credential is invalid")
        self._session_identity_credentials[session_id] = (
            normalized_provider,
            normalized_token,
        )

    def _session_identity_credential(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> tuple[str, str]:
        self.validate_session(session_id, now)
        credential = self._session_identity_credentials.get(session_id)
        if credential is None:
            raise DesktopIdentityError(
                "Desktop identity credential is unavailable"
            )
        return credential

    def list_li_memories(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> tuple[dict[str, object], ...]:
        raise DesktopIdentityError("Desktop Li memory transport is unavailable")

    def remember_li_memory(
        self,
        session_id: str,
        *,
        kind: str,
        content: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        raise DesktopIdentityError("Desktop Li memory transport is unavailable")

    def logout(self, session_id: str) -> None:
        self._session_registry.revoke_session(session_id)
        self._session_tenants.pop(session_id, None)
        self._session_li_founder.pop(session_id, None)
        self._session_identity_credentials.pop(session_id, None)
        stale_states = [
            state
            for state, result in self._results.items()
            if result.session_id == session_id
        ]
        for state in stale_states:
            self._results.pop(state, None)

    def _purge(self, now: datetime) -> None:
        expired_states = [
            state for state, flow in self._flows.items() if flow.expires_at <= now
        ]
        for state in expired_states:
            self._flows.pop(state, None)
        if len(self._results) > 100:
            for state in tuple(self._results)[:-100]:
                self._results.pop(state, None)


class _PyJwtOIDCTokenVerifier(OIDCTokenVerifier):
    def __init__(self, provider: OIDCProviderConfig, *, expected_nonce: str) -> None:
        self._provider = provider
        self._expected_nonce = expected_nonce
        self.verified_expires_at: datetime | None = None

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        try:
            import jwt

            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            if not isinstance(algorithm, str) or algorithm not in _ALLOWED_ALGORITHMS:
                raise DesktopIdentityError("OIDC signing algorithm is not allowed")
            key = jwt.PyJWKClient(self._provider.jwks_uri).get_signing_key_from_jwt(
                encoded_token
            )
            claims = jwt.decode(
                encoded_token,
                key.key,
                algorithms=[algorithm],
                audience=self._provider.client_id,
                issuer=self._provider.issuer,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "nonce"]
                },
            )
        except DesktopIdentityError:
            raise
        except Exception as error:
            raise DesktopIdentityError("OIDC ID token verification failed") from error
        if claims.get("nonce") != self._expected_nonce:
            raise DesktopIdentityError("OIDC nonce validation failed")

        subject = _claim_text(claims, "sub")
        issuer = _claim_text(claims, "iss")
        issued_at = _claim_time(claims, "iat")
        expires_at = _claim_time(claims, "exp")
        self.verified_expires_at = expires_at
        tenant_id = "desktop-" + hashlib.sha256(
            f"{issuer}\0{subject}".encode("utf-8")
        ).hexdigest()[:24]
        attributes: set[tuple[str, str]] = set()
        email = claims.get("email")
        if isinstance(email, str) and claims.get("email_verified") is True:
            attributes.add(("verified_email", email.strip().casefold()))
        methods = claims.get("amr", [])
        authentication_methods = (
            frozenset(
                value for value in methods if isinstance(value, str) and value.strip()
            )
            if isinstance(methods, list)
            else frozenset()
        )
        return VerifiedOIDCClaims(
            issuer=issuer,
            audience=self._provider.client_id,
            subject=subject,
            tenant_id=tenant_id,
            expires_at=expires_at,
            issued_at=issued_at,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset(attributes),
            authentication_methods=authentication_methods,
        )


def _validate_provider(provider: OIDCProviderConfig) -> OIDCProviderConfig:
    if _PROVIDER_ID.fullmatch(provider.provider_id) is None:
        raise DesktopIdentityError("Desktop OIDC provider_id is invalid")
    if not provider.display_name.strip() or not provider.client_id.strip():
        raise DesktopIdentityError("Desktop OIDC provider identity is incomplete")
    for name, value in (
        ("issuer", provider.issuer),
        ("authorization_endpoint", provider.authorization_endpoint),
        ("token_endpoint", provider.token_endpoint),
        ("jwks_uri", provider.jwks_uri),
    ):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.fragment:
            raise DesktopIdentityError(
                f"Desktop OIDC {name} must be an HTTPS URL"
            )
    if "openid" not in provider.scopes:
        raise DesktopIdentityError("Desktop OIDC provider must request openid scope")
    return provider


def _validate_loopback_redirect(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.port is None
        or parsed.path != "/oauth/callback"
        or parsed.query
        or parsed.fragment
    ):
        raise DesktopIdentityError(
            "Desktop OIDC redirect must be the loopback callback"
        )


def _required_text(document: Mapping[str, Any], name: str) -> str:
    value = document.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DesktopIdentityError(f"Desktop OIDC {name} is required")
    return value.strip()


def _optional_text(document: Mapping[str, Any], name: str) -> str | None:
    value = document.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DesktopIdentityError(f"Desktop OIDC {name} must be a non-empty string")
    return value.strip()


def _safe_provider_error_code(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("error")
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    if _PROVIDER_ERROR_CODE.fullmatch(normalized) is None:
        return None
    return normalized


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise DesktopIdentityError(
            "Desktop identity timestamps must be timezone-aware"
        )
    return current.astimezone(timezone.utc)


def _claim_text(claims: Mapping[str, Any], name: str) -> str:
    value = claims.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DesktopIdentityError(f"OIDC {name} claim is required")
    return value.strip()


def _claim_time(claims: Mapping[str, Any], name: str) -> datetime:
    value = claims.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DesktopIdentityError(f"OIDC {name} claim is invalid")
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _verified_email(principal: Principal) -> str | None:
    for key, value in principal.attributes:
        if key == "verified_email":
            return value
    return None
