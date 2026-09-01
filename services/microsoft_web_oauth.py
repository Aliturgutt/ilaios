"""Production Microsoft Web OIDC Authorization Code + PKCE boundary.

This adapter verifies Microsoft personal/work/school identities before handing a
provider-neutral VerifiedExternalIdentity to canonical CentralIdentityService.
Raw provider credentials and tokens never leave this module.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlencode
from uuid import UUID

import jwt
import requests

from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.email_auth import EmailChallenge, EmailChallengeStore

_FLOW_LIFETIME = timedelta(minutes=5)
_STATE_PREFIX = "msa_"
_REPLAY_SENTINEL = "microsoft-web-oauth@internal.invalid"
_AUTHORIZATION_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
_ISSUER_TEMPLATE = "https://login.microsoftonline.com/{tenantid}/v2.0"
_ALLOWED_ALGORITHMS = frozenset({"RS256"})


class MicrosoftWebOAuthError(PermissionError):
    """Microsoft Web OAuth evidence is missing, stale, replayed, or invalid."""


class MicrosoftWebOAuthStateError(MicrosoftWebOAuthError):
    """OAuth state is malformed, expired, replayed, or invalid."""


class MicrosoftWebOAuthTokenExchangeError(MicrosoftWebOAuthError):
    """Microsoft token endpoint did not return an acceptable response."""


class MicrosoftWebOAuthIDTokenError(MicrosoftWebOAuthError):
    """Microsoft ID token did not verify under the configured policy."""


@dataclass(frozen=True, slots=True)
class MicrosoftWebOAuthCredentials:
    client_id: str
    client_secret: str
    state_secret: str

    @classmethod
    def from_environment_optional(
        cls, env: Mapping[str, str]
    ) -> MicrosoftWebOAuthCredentials | None:
        keys = (
            "ILAIOS_MICROSOFT_WEB_CLIENT_ID",
            "ILAIOS_MICROSOFT_WEB_CLIENT_SECRET",
            "ILAIOS_MICROSOFT_WEB_OAUTH_STATE_SECRET",
        )
        values = tuple(env.get(key, "").strip() for key in keys)
        if not any(values):
            return None
        if not all(values):
            raise MicrosoftWebOAuthError(
                "Microsoft Web OAuth configuration is incomplete"
            )
        client_id, client_secret, state_secret = values
        try:
            UUID(client_id)
        except ValueError as error:
            raise MicrosoftWebOAuthError(
                "Microsoft Web OAuth client id is invalid"
            ) from error
        if len(client_secret) < 16:
            raise MicrosoftWebOAuthError(
                "Microsoft Web OAuth client secret is unavailable or too short"
            )
        if len(state_secret) < 32:
            raise MicrosoftWebOAuthError(
                "Microsoft Web OAuth state secret is unavailable or too short"
            )
        if secrets.compare_digest(client_secret, state_secret):
            raise MicrosoftWebOAuthError(
                "Microsoft Web OAuth state secret must differ from client secret"
            )
        return cls(client_id, client_secret, state_secret)


class MicrosoftWebOAuthReplayStore(Protocol):
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


class IdentityChallengeMicrosoftWebOAuthReplayStore:
    """Reuse the incumbent canonical one-use identity challenge ledger."""

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
            raise MicrosoftWebOAuthError("Microsoft OAuth replay marker is invalid")
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
        return (
            self._store.consume(
                challenge_id=challenge_id,
                email=_REPLAY_SENTINEL,
                secret_digest=state_digest,
                now=_utc(now),
            )
            is not None
        )


@dataclass(frozen=True, slots=True)
class MicrosoftWebOAuthStart:
    state: str
    authorization_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class MicrosoftWebOAuthCompletion:
    identity: VerifiedExternalIdentity
    purpose: str


class MicrosoftIdentityTokenVerifier(Protocol):
    def verify(self, encoded_token: str) -> VerifiedExternalIdentity: ...


class MicrosoftWebOAuthService:
    def __init__(
        self,
        *,
        credentials: MicrosoftWebOAuthCredentials,
        replay_store: MicrosoftWebOAuthReplayStore,
        request_session: requests.Session | None = None,
        verifier_factory: Any | None = None,
    ) -> None:
        self._credentials = credentials
        self._replay_store = replay_store
        self._http = request_session or requests.Session()
        self._verifier_factory = verifier_factory or (
            lambda expected_nonce, current: _MicrosoftIDTokenVerifier(
                client_id=credentials.client_id,
                expected_nonce=expected_nonce,
                now=current,
            )
        )

    def start(
        self,
        *,
        redirect_uri: str,
        now: datetime,
        purpose: str = "signin",
    ) -> MicrosoftWebOAuthStart:
        current = _utc(now)
        _validate_redirect(redirect_uri)
        purpose_marker = _purpose_marker(purpose)
        challenge_id = f"{_STATE_PREFIX}{secrets.token_hex(16)}"
        random_state = secrets.token_urlsafe(32)
        state = f"{challenge_id}.{purpose_marker}.{random_state}"
        expires_at = current + _FLOW_LIFETIME
        self._replay_store.put(
            challenge_id=challenge_id,
            state_digest=_digest(state),
            issued_at=current,
            expires_at=expires_at,
        )
        verifier = _derive(self._credentials.state_secret, "pkce", state, size=64)
        nonce = _derive(self._credentials.state_secret, "nonce", state, size=48)
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        query = urlencode(
            {
                "client_id": self._credentials.client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "response_mode": "query",
                "scope": "openid profile email",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
        )
        return MicrosoftWebOAuthStart(
            state=state,
            authorization_url=f"{_AUTHORIZATION_ENDPOINT}?{query}",
            expires_at=expires_at,
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        redirect_uri: str,
        now: datetime,
    ) -> MicrosoftWebOAuthCompletion:
        current = _utc(now)
        _validate_redirect(redirect_uri)
        challenge_id, purpose = _state_coordinates(state)
        normalized_code = _opaque(code, "authorization code")
        if not self._replay_store.consume(
            challenge_id=challenge_id,
            state_digest=_digest(state),
            now=current,
        ):
            raise MicrosoftWebOAuthStateError(
                "Microsoft OAuth state is invalid, expired, or already used"
            )
        verifier = _derive(self._credentials.state_secret, "pkce", state, size=64)
        nonce = _derive(self._credentials.state_secret, "nonce", state, size=48)
        try:
            response = self._http.post(
                _TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._credentials.client_id,
                    "client_secret": self._credentials.client_secret,
                    "code": normalized_code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": verifier,
                    "scope": "openid profile email",
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise MicrosoftWebOAuthTokenExchangeError(
                "Microsoft token exchange failed"
            ) from error
        try:
            payload = response.json()
            response.raise_for_status()
        except (ValueError, requests.RequestException) as error:
            raise MicrosoftWebOAuthTokenExchangeError(
                "Microsoft token exchange failed"
            ) from error
        if not isinstance(payload, dict):
            raise MicrosoftWebOAuthTokenExchangeError(
                "Microsoft token response is malformed"
            )
        encoded_token = payload.get("id_token")
        if not isinstance(encoded_token, str) or not encoded_token.strip():
            raise MicrosoftWebOAuthTokenExchangeError(
                "Microsoft token response did not contain an ID token"
            )
        try:
            verified = self._verifier_factory(nonce, current).verify(encoded_token)
        except MicrosoftWebOAuthError:
            raise
        except Exception as error:
            raise MicrosoftWebOAuthIDTokenError(
                "Microsoft ID token verification failed"
            ) from error
        if verified.provider is not IdentityProvider.MICROSOFT:
            raise MicrosoftWebOAuthIDTokenError(
                "Microsoft verifier returned wrong provider"
            )
        return MicrosoftWebOAuthCompletion(
            identity=verified.normalized(),
            purpose=purpose,
        )


class _MicrosoftIDTokenVerifier:
    def __init__(
        self,
        *,
        client_id: str,
        expected_nonce: str,
        now: datetime,
    ) -> None:
        self._client_id = client_id
        self._expected_nonce = expected_nonce
        self._now = _utc(now)

    def verify(self, encoded_token: str) -> VerifiedExternalIdentity:
        try:
            header = jwt.get_unverified_header(encoded_token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if algorithm not in _ALLOWED_ALGORITHMS or not isinstance(kid, str):
                raise MicrosoftWebOAuthIDTokenError(
                    "Microsoft signing algorithm or key id is invalid"
                )
            client = jwt.PyJWKClient(_JWKS_URI)
            key = client.get_signing_key_from_jwt(encoded_token)
            claims = jwt.decode(
                encoded_token,
                key.key,
                algorithms=[str(algorithm)],
                audience=self._client_id,
                options={
                    "verify_iss": False,
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "oid",
                        "tid",
                        "nonce",
                    ],
                },
            )
        except MicrosoftWebOAuthError:
            raise
        except Exception as error:
            raise MicrosoftWebOAuthIDTokenError(
                "Microsoft ID token signature or claims are invalid"
            ) from error
        if claims.get("nonce") != self._expected_nonce:
            raise MicrosoftWebOAuthIDTokenError("Microsoft nonce validation failed")
        tenant_id = _canonical_uuid(claims.get("tid"), "tid")
        object_id = _canonical_uuid(claims.get("oid"), "oid")
        issuer = claims.get("iss")
        if not isinstance(issuer, str) or issuer != _ISSUER_TEMPLATE.replace(
            "{tenantid}", tenant_id
        ):
            raise MicrosoftWebOAuthIDTokenError(
                "Microsoft tenant/issuer binding failed"
            )
        _validate_signing_key_issuer(client, str(kid), tenant_id, issuer)
        _validate_temporal_claims(claims, self._now)
        return VerifiedExternalIdentity(
            provider=IdentityProvider.MICROSOFT,
            subject=object_id,
            issuer=issuer,
        )



def _validate_temporal_claims(
    claims: Mapping[str, Any],
    current: datetime,
) -> None:
    issued_at = _claim_time(claims, "iat")
    expires_at = _claim_time(claims, "exp")
    if issued_at > current + timedelta(minutes=5):
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft ID token issued-at claim is in the future"
        )
    if expires_at <= current:
        raise MicrosoftWebOAuthIDTokenError("Microsoft ID token is expired")

def _validate_signing_key_issuer(
    client: jwt.PyJWKClient,
    kid: str,
    tenant_id: str,
    token_issuer: str,
) -> None:
    try:
        document = client.fetch_data()
    except Exception as error:
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft signing-key metadata is unavailable"
        ) from error
    keys = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(keys, list):
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft signing-key metadata is malformed"
        )
    matches = [
        item for item in keys if isinstance(item, dict) and item.get("kid") == kid
    ]
    if len(matches) != 1:
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft signing-key metadata is ambiguous"
        )
    issuer = matches[0].get("issuer")
    if not isinstance(issuer, str):
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft signing-key issuer is missing"
        )
    if issuer.replace("{tenantid}", tenant_id) != token_issuer:
        raise MicrosoftWebOAuthIDTokenError(
            "Microsoft signing-key issuer binding failed"
        )


def _state_coordinates(state: str) -> tuple[str, str]:
    normalized = _opaque(state, "state")
    parts = normalized.split(".", 2)
    if len(parts) != 3 or not parts[0].startswith(_STATE_PREFIX):
        raise MicrosoftWebOAuthStateError("Microsoft OAuth state format is invalid")
    if len(parts[0]) != len(_STATE_PREFIX) + 32 or len(parts[2]) < 32:
        raise MicrosoftWebOAuthStateError("Microsoft OAuth state format is invalid")
    purpose = {"s": "signin", "l": "link"}.get(parts[1])
    if purpose is None:
        raise MicrosoftWebOAuthStateError("Microsoft OAuth state purpose is invalid")
    return parts[0], purpose


def _purpose_marker(purpose: str) -> str:
    marker = {"signin": "s", "link": "l"}.get(purpose)
    if marker is None:
        raise MicrosoftWebOAuthError("Microsoft OAuth purpose is invalid")
    return marker


def _validate_redirect(value: str) -> None:
    if value != "https://app.ilaios.com/auth/microsoft/callback":
        raise MicrosoftWebOAuthError("Microsoft Web OAuth redirect URI is invalid")


def _canonical_uuid(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise MicrosoftWebOAuthIDTokenError(f"Microsoft {field} claim is invalid")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise MicrosoftWebOAuthIDTokenError(
            f"Microsoft {field} claim is invalid"
        ) from error
    normalized = str(parsed)
    if normalized.casefold() != value.casefold():
        raise MicrosoftWebOAuthIDTokenError(
            f"Microsoft {field} claim is not canonical"
        )
    return normalized


def _claim_time(claims: Mapping[str, Any], key: str) -> datetime:
    value = claims.get(key)
    if not isinstance(value, (int, float)):
        raise MicrosoftWebOAuthIDTokenError(
            f"Microsoft {key} claim is invalid"
        )
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _derive(secret: str, purpose: str, state: str, *, size: int) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{purpose}\0{state}".encode("utf-8"),
        hashlib.sha512,
    ).digest()
    encoded = _base64url(digest)
    return encoded[:size]


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _opaque(value: str, field: str) -> str:
    normalized = value.strip()
    if normalized != value or not 8 <= len(normalized) <= 4096:
        raise MicrosoftWebOAuthError(f"Microsoft {field} is invalid")
    if any(character.isspace() or ord(character) < 0x20 for character in normalized):
        raise MicrosoftWebOAuthError(f"Microsoft {field} is invalid")
    return normalized


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MicrosoftWebOAuthError(
            "Microsoft OAuth timestamps must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


__all__ = [
    "IdentityChallengeMicrosoftWebOAuthReplayStore",
    "MicrosoftWebOAuthCompletion",
    "MicrosoftWebOAuthCredentials",
    "MicrosoftWebOAuthError",
    "MicrosoftWebOAuthIDTokenError",
    "MicrosoftWebOAuthService",
    "MicrosoftWebOAuthStart",
    "MicrosoftWebOAuthStateError",
    "MicrosoftWebOAuthTokenExchangeError",
]
