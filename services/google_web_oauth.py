"""Production Google Web OAuth Authorization Code + PKCE boundary.

This adapter owns only provider-flow verification. Canonical account, tenant,
membership, role, session, entitlement, and persistence authority remains in the
existing central Identity services. Raw Google credentials and tokens never
leave this adapter.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlencode

import requests

from services.central_identity import VerifiedExternalIdentity
from services.email_auth import EmailChallenge, EmailChallengeStore
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
_STATE_PREFIX = "goa_"
_REPLAY_SENTINEL = "google-web-oauth@internal.invalid"
VerifierFactory = Callable[[str, str], OIDCTokenVerifier]


class GoogleWebOAuthError(PermissionError):
    """Google Web OAuth evidence is missing, stale, replayed, or invalid."""


class GoogleWebOAuthStateError(GoogleWebOAuthError):
    """OAuth state is malformed, expired, replayed, or fails redirect binding."""


class GoogleWebOAuthTokenExchangeError(GoogleWebOAuthError):
    """The provider token endpoint did not return an acceptable response."""


class GoogleWebOAuthIDTokenVerificationError(GoogleWebOAuthError):
    """The returned Google ID token cannot be verified under policy."""


class GoogleWebOAuthJwksResolutionError(GoogleWebOAuthIDTokenVerificationError):
    """Google JWKS retrieval or signing-key resolution failed."""


class GoogleWebOAuthJWTDecodeError(GoogleWebOAuthIDTokenVerificationError):
    """Google ID token signature or cryptographic decoding failed."""


class GoogleWebOAuthIssuerAudienceError(GoogleWebOAuthIDTokenVerificationError):
    """Google ID token issuer or audience failed validation."""


class GoogleWebOAuthNonceError(GoogleWebOAuthIDTokenVerificationError):
    """Google ID token nonce failed validation."""


class GoogleWebOAuthTemporalClaimsError(GoogleWebOAuthIDTokenVerificationError):
    """Google ID token temporal claims failed validation."""


class GoogleWebOAuthMalformedClaimsError(GoogleWebOAuthIDTokenVerificationError):
    """Google ID token claims were malformed or incomplete."""


@dataclass(frozen=True, slots=True)
class GoogleWebOAuthCredentials:
    """Server-only Google Web OAuth credentials and state-derivation secret."""

    client_secret: str
    state_secret: str

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> GoogleWebOAuthCredentials:
        client_secret = env.get(
            "ILAIOS_GOOGLE_PRODUCTION_WEB_CLIENT_SECRET", ""
        ).strip()
        state_secret = env.get("ILAIOS_GOOGLE_WEB_OAUTH_STATE_SECRET", "").strip()
        if len(client_secret) < 16:
            raise GoogleWebOAuthError(
                "Google production Web client secret is unavailable or too short"
            )
        if len(state_secret) < 32:
            raise GoogleWebOAuthError(
                "Google Web OAuth state secret is unavailable or too short"
            )
        if secrets.compare_digest(client_secret, state_secret):
            raise GoogleWebOAuthError(
                "Google Web OAuth state secret must be distinct from client secret"
            )
        return cls(client_secret=client_secret, state_secret=state_secret)


class GoogleWebOAuthReplayStore(Protocol):
    """Durable one-use replay marker store; raw OAuth state is never persisted."""

    def put(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> None: ...

    def consume(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        now: datetime,
    ) -> bool: ...


class IdentityChallengeGoogleWebOAuthReplayStore:
    """Reuse the incumbent canonical Identity one-use challenge ledger.

    Production composition should provide ``SQLiteEmailChallengeStore`` backed
    by the canonical identity database. The table is reused only as an opaque
    one-use challenge ledger: no email identity semantics or raw OAuth secrets
    are introduced, and no second schema/migration authority is created.
    """

    def __init__(self, store: EmailChallengeStore) -> None:
        self._store = store

    def put(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> None:
        if not challenge_id.startswith(_STATE_PREFIX) or len(state_digest) != 64:
            raise GoogleWebOAuthError("OAuth replay marker is invalid")
        self._store.put(
            EmailChallenge(
                challenge_id=challenge_id,
                email=_REPLAY_SENTINEL,
                secret_digest=state_digest,
                issued_at=_utc(issued_at),
                expires_at=_utc(expires_at),
            )
        )

    def consume(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        now: datetime,
    ) -> bool:
        consumed = self._store.consume(
            challenge_id=challenge_id,
            email=_REPLAY_SENTINEL,
            secret_digest=state_digest,
            now=_utc(now),
        )
        return consumed is not None


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
        replay_store: GoogleWebOAuthReplayStore,
        request_session: requests.Session | None = None,
        verifier_factory: VerifierFactory | None = None,
    ) -> None:
        self._oidc = oidc
        self._credentials = credentials
        self._replay_store = replay_store
        self._http = request_session or requests.Session()
        self._verifier_factory = verifier_factory or (
            lambda client_id, nonce: _GoogleIDTokenVerifier(
                client_id=client_id, expected_nonce=nonce
            )
        )

    def start(self, *, redirect_uri: str, now: datetime) -> GoogleWebOAuthStart:
        current = _utc(now)
        redirect = self._oidc.require_production_web_redirect(redirect_uri)
        redirect_index = self._oidc.production_web_redirects.index(redirect)
        challenge_id = f"{_STATE_PREFIX}{secrets.token_hex(16)}"
        random_state = secrets.token_urlsafe(32)
        state = f"{challenge_id}.{redirect_index}.{random_state}"
        expires_at = current + _FLOW_LIFETIME
        self._replay_store.put(
            challenge_id=challenge_id,
            state_digest=_state_digest(state),
            issued_at=current,
            expires_at=expires_at,
        )
        nonce = _derive(self._credentials.state_secret, "nonce", state, size=32)
        verifier = _derive(
            self._credentials.state_secret,
            "pkce-verifier",
            state,
            size=64,
        )
        challenge = _base64url(
            hashlib.sha256(verifier.encode("ascii")).digest()
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
        try:
            normalized_state = _opaque(state, "OAuth state")
            normalized_code = _opaque(code, "authorization code")
            challenge_id, redirect_index = _state_coordinates(normalized_state)
            if not self._replay_store.consume(
                challenge_id=challenge_id,
                state_digest=_state_digest(normalized_state),
                now=current,
            ):
                raise GoogleWebOAuthError("OAuth state is invalid, expired, or replayed")
            redirect = self._oidc.production_web_redirects[redirect_index]
            redirect = self._oidc.require_production_web_redirect(redirect)
            nonce = _derive(
                self._credentials.state_secret,
                "nonce",
                normalized_state,
                size=32,
            )
            verifier_value = _derive(
                self._credentials.state_secret,
                "pkce-verifier",
                normalized_state,
                size=64,
            )
        except (GoogleWebOAuthError, IndexError) as error:
            raise GoogleWebOAuthStateError(str(error)) from error

        try:
            response = self._http.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._oidc.production_web_client_id,
                    "client_secret": self._credentials.client_secret,
                    "code": normalized_code,
                    "redirect_uri": redirect,
                    "code_verifier": verifier_value,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise GoogleWebOAuthTokenExchangeError(
                "Google token exchange failed"
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise GoogleWebOAuthTokenExchangeError(
                "Google token response is malformed"
            ) from error
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise GoogleWebOAuthTokenExchangeError(
                "Google token exchange failed"
            ) from error
        if not isinstance(payload, dict):
            raise GoogleWebOAuthTokenExchangeError("Google token response is malformed")
        encoded_token = payload.get("id_token")
        if not isinstance(encoded_token, str) or not encoded_token.strip():
            raise GoogleWebOAuthTokenExchangeError(
                "Google token response did not contain an ID token"
            )

        token_verifier = self._verifier_factory(
            self._oidc.production_web_client_id, nonce
        )
        try:
            claims = token_verifier.verify(encoded_token)
            _validate_verified_claims(
                claims,
                client_id=self._oidc.production_web_client_id,
                now=current,
            )
            return verified_google_identity(claims)
        except GoogleWebOAuthIDTokenVerificationError:
            raise
        except Exception as error:
            raise GoogleWebOAuthIDTokenVerificationError(
                "Google ID token verification failed"
            ) from error


class _GoogleIDTokenVerifier(OIDCTokenVerifier):
    def __init__(self, *, client_id: str, expected_nonce: str) -> None:
        self._client_id = client_id
        self._expected_nonce = expected_nonce

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        import jwt

        try:
            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            if not isinstance(algorithm, str) or algorithm not in _ALLOWED_ALGORITHMS:
                raise GoogleWebOAuthMalformedClaimsError(
                    "Google ID token algorithm is not allowed"
                )
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
        except jwt.PyJWKClientError as error:
            raise GoogleWebOAuthJwksResolutionError(
                "Google JWKS signing key resolution failed"
            ) from error
        except (jwt.InvalidIssuerError, jwt.InvalidAudienceError) as error:
            raise GoogleWebOAuthIssuerAudienceError(
                "Google ID token issuer or audience rejected"
            ) from error
        except (jwt.ExpiredSignatureError, jwt.ImmatureSignatureError) as error:
            raise GoogleWebOAuthTemporalClaimsError(
                "Google ID token temporal claims rejected"
            ) from error
        except jwt.InvalidTokenError as error:
            raise GoogleWebOAuthJWTDecodeError(
                "Google ID token signature or decoding failed"
            ) from error
        except GoogleWebOAuthIDTokenVerificationError:
            raise
        except Exception as error:
            raise GoogleWebOAuthMalformedClaimsError(
                "Google ID token claims are malformed"
            ) from error
        if claims.get("nonce") != self._expected_nonce:
            raise GoogleWebOAuthNonceError("Google OIDC nonce validation failed")

        try:
            subject = _claim_text(claims, "sub")
            issuer = _claim_text(claims, "iss")
            issued_at = _claim_time(claims, "iat")
            expires_at = _claim_time(claims, "exp")
        except GoogleWebOAuthError as error:
            raise GoogleWebOAuthMalformedClaimsError(
                "Google ID token claims are malformed"
            ) from error
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


def _state_coordinates(state: str) -> tuple[str, int]:
    parts = state.split(".")
    if len(parts) != 3:
        raise GoogleWebOAuthError("OAuth state format is invalid")
    challenge_id, raw_index, random_state = parts
    if not challenge_id.startswith(_STATE_PREFIX) or len(challenge_id) != 36:
        raise GoogleWebOAuthError("OAuth state challenge binding is invalid")
    if not random_state or len(random_state) < 32:
        raise GoogleWebOAuthError("OAuth state entropy is invalid")
    try:
        redirect_index = int(raw_index)
    except ValueError as error:
        raise GoogleWebOAuthError("OAuth state redirect binding is invalid") from error
    if redirect_index < 0 or redirect_index > 32:
        raise GoogleWebOAuthError("OAuth state redirect binding is invalid")
    return challenge_id, redirect_index


def _state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _derive(secret: str, purpose: str, state: str, *, size: int) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{purpose}\0{state}".encode("utf-8"),
        hashlib.sha512,
    ).digest()
    value = _base64url(digest)
    if size < 1 or size > len(value):
        raise GoogleWebOAuthError("OAuth derivation policy is invalid")
    return value[:size]


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
    if value.tzinfo is None or value.utcoffset() is None:
        raise GoogleWebOAuthError("OAuth timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
