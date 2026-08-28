"""Production Google Web OAuth Authorization Code + PKCE boundary.

This adapter owns only provider-flow verification. Canonical account, tenant,
membership, role, session, and entitlement authority remains in the existing
central Identity services. Raw Google credentials and tokens never leave this
adapter.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, cast
from urllib.parse import urlencode

import requests

from services.central_identity import VerifiedExternalIdentity
from services.google_oidc import (
    GOOGLE_AUTHORIZATION_ENDPOINT,
    GOOGLE_ISSUER,
    GOOGLE_JWKS_URI,
    GOOGLE_TOKEN_ENDPOINT,
    GoogleOIDCEnvironment,
    verified_google_identity,
)
from services.identity import IdentityKind, OIDCTokenVerifier, VerifiedOIDCClaims

_FLOW_LIFETIME = timedelta(minutes=5)
_MAX_ID_TOKEN_LIFETIME = timedelta(hours=2)
_ALLOWED_ALGORITHMS = frozenset({"RS256"})
VerifierFactory = Callable[[str, str], OIDCTokenVerifier]


class GoogleWebOAuthError(PermissionError):
    """Google Web OAuth evidence is missing, stale, replayed, or invalid."""


@dataclass(frozen=True, slots=True)
class GoogleWebOAuthCredentials:
    client_secret: str

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> GoogleWebOAuthCredentials:
        secret = env.get("ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_SECRET", "").strip()
        if not secret:
            raise GoogleWebOAuthError("Google production Web client secret is required")
        return cls(client_secret=secret)


@dataclass(frozen=True, slots=True)
class GoogleWebOAuthFlow:
    state_digest: str
    nonce: str
    code_verifier: str
    redirect_uri: str
    issued_at: datetime
    expires_at: datetime


class GoogleWebOAuthFlowStore(Protocol):
    """One-use server-side flow persistence; production adapters must be durable."""

    def create_flow(self, flow: GoogleWebOAuthFlow) -> None: ...

    def consume_flow(
        self, *, state_digest: str, now: datetime
    ) -> GoogleWebOAuthFlow | None: ...


class InMemoryGoogleWebOAuthFlowStore:
    """Deterministic local/test store; not a production persistence claim."""

    def __init__(self) -> None:
        self._flows: dict[str, GoogleWebOAuthFlow] = {}

    def create_flow(self, flow: GoogleWebOAuthFlow) -> None:
        if flow.state_digest in self._flows:
            raise GoogleWebOAuthError("OAuth state collision")
        self._flows[flow.state_digest] = flow

    def consume_flow(
        self, *, state_digest: str, now: datetime
    ) -> GoogleWebOAuthFlow | None:
        flow = self._flows.pop(state_digest, None)
        if flow is None or flow.expires_at <= _utc(now):
            return None
        return flow


@dataclass(frozen=True, slots=True)
class GoogleWebOAuthStart:
    state: str
    authorization_url: str
    expires_at: datetime


class GoogleWebOAuthService:
    """Verify a Google Web OAuth callback before canonical account resolution."""

    def __init__(
        self,
        *,
        oidc: GoogleOIDCEnvironment,
        credentials: GoogleWebOAuthCredentials,
        flows: GoogleWebOAuthFlowStore,
        request_session: requests.Session | None = None,
        verifier_factory: VerifierFactory | None = None,
    ) -> None:
        self._oidc = oidc
        self._credentials = credentials
        self._flows = flows
        self._http = request_session or requests.Session()
        self._verifier_factory = verifier_factory or (
            lambda client_id, nonce: _GoogleIDTokenVerifier(
                client_id=client_id, expected_nonce=nonce
            )
        )

    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
        current = _utc(now)
        redirect = self._oidc.require_production_web_redirect(redirect_uri)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        expires_at = current + _FLOW_LIFETIME
        self._flows.create_flow(
            GoogleWebOAuthFlow(
                state_digest=_state_digest(state),
                nonce=nonce,
                code_verifier=verifier,
                redirect_uri=redirect,
                issued_at=current,
                expires_at=expires_at,
            )
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._oidc.production_web_client_id,
                "redirect_uri": redirect,
                "scope": "openid profile email",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return GoogleWebOAuthStart(
            state=state,
            authorization_url=f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}",
            expires_at=expires_at,
        )

    def complete(
        self, *, state: str, code: str, now: datetime
    ) -> VerifiedExternalIdentity:
        current = _utc(now)
        normalized_state = _opaque(state, "OAuth state")
        normalized_code = _opaque(code, "authorization code")
        flow = self._flows.consume_flow(
            state_digest=_state_digest(normalized_state), now=current
        )
        if flow is None:
            raise GoogleWebOAuthError("OAuth state is invalid, expired, or replayed")
        if flow.issued_at > current or flow.expires_at <= current:
            raise GoogleWebOAuthError("OAuth flow is not currently valid")

        try:
            response = self._http.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._oidc.production_web_client_id,
                    "client_secret": self._credentials.client_secret,
                    "code": normalized_code,
                    "redirect_uri": flow.redirect_uri,
                    "code_verifier": flow.code_verifier,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise GoogleWebOAuthError("Google token exchange failed") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise GoogleWebOAuthError("Google token response is malformed") from error
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise GoogleWebOAuthError("Google token exchange failed") from error
        if not isinstance(payload, dict):
            raise GoogleWebOAuthError("Google token response is malformed")
        encoded_token = payload.get("id_token")
        if not isinstance(encoded_token, str) or not encoded_token.strip():
            raise GoogleWebOAuthError("Google token response did not contain an ID token")

        verifier = self._verifier_factory(
            self._oidc.production_web_client_id, flow.nonce
        )
        try:
            claims = verifier.verify(encoded_token)
        except Exception as error:
            raise GoogleWebOAuthError("Google ID token verification failed") from error
        _validate_verified_claims(
            claims,
            client_id=self._oidc.production_web_client_id,
            now=current,
        )
        return verified_google_identity(claims)


class _GoogleIDTokenVerifier(OIDCTokenVerifier):
    def __init__(self, *, client_id: str, expected_nonce: str) -> None:
        self._client_id = client_id
        self._expected_nonce = expected_nonce

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        try:
            import jwt

            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            if not isinstance(algorithm, str) or algorithm not in _ALLOWED_ALGORITHMS:
                raise GoogleWebOAuthError("Google ID token algorithm is not allowed")
            key = jwt.PyJWKClient(GOOGLE_JWKS_URI).get_signing_key_from_jwt(encoded_token)
            claims = jwt.decode(
                encoded_token,
                key.key,
                algorithms=[algorithm],
                audience=self._client_id,
                issuer=GOOGLE_ISSUER,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "nonce"]
                },
            )
        except GoogleWebOAuthError:
            raise
        except Exception as error:
            raise GoogleWebOAuthError("Google ID token cryptographic verification failed") from error
        if claims.get("nonce") != self._expected_nonce:
            raise GoogleWebOAuthError("Google OIDC nonce validation failed")

        subject = _claim_text(claims, "sub")
        issuer = _claim_text(claims, "iss")
        issued_at = _claim_time(claims, "iat")
        expires_at = _claim_time(claims, "exp")
        attributes: set[tuple[str, str]] = set()
        email = claims.get("email")
        if isinstance(email, str) and claims.get("email_verified") is True:
            normalized_email = email.strip().casefold()
            if normalized_email:
                attributes.add(("verified_email", normalized_email))
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
            audience=self._client_id,
            subject=subject,
            tenant_id="external-google-unresolved",
            expires_at=expires_at,
            issued_at=issued_at,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset(attributes),
            authentication_methods=authentication_methods,
        )


def _validate_verified_claims(
    claims: VerifiedOIDCClaims, *, client_id: str, now: datetime
) -> None:
    if claims.issuer != GOOGLE_ISSUER:
        raise GoogleWebOAuthError("Google ID token issuer mismatch")
    if claims.audience != client_id:
        raise GoogleWebOAuthError("Google ID token audience mismatch")
    if claims.issued_at > now or claims.expires_at <= now:
        raise GoogleWebOAuthError("Google ID token is not currently valid")
    if claims.expires_at - claims.issued_at > _MAX_ID_TOKEN_LIFETIME:
        raise GoogleWebOAuthError("Google ID token lifetime exceeds policy")
    if not claims.subject.strip():
        raise GoogleWebOAuthError("Google ID token subject is required")


def _state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _opaque(value: str, field: str) -> str:
    normalized = value.strip()
    if normalized != value or not 8 <= len(normalized) <= 4096:
        raise GoogleWebOAuthError(f"{field} is invalid")
    if any(character.isspace() or ord(character) < 0x20 for character in normalized):
        raise GoogleWebOAuthError(f"{field} is invalid")
    return normalized


def _claim_text(claims: Mapping[str, Any], key: str) -> str:
    value = claims.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoogleWebOAuthError(f"Google ID token {key} claim is invalid")
    return value.strip()


def _claim_time(claims: Mapping[str, Any], key: str) -> datetime:
    value = claims.get(key)
    if not isinstance(value, (int, float)):
        raise GoogleWebOAuthError(f"Google ID token {key} claim is invalid")
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise GoogleWebOAuthError("OAuth timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
