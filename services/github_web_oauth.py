"""Production GitHub OAuth Authorization Code + PKCE boundary.

This adapter verifies the GitHub account through GitHub's user API and returns a
provider-neutral VerifiedExternalIdentity. Raw access tokens never leave this
module and are never persisted or logged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlencode

import requests

from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.email_auth import EmailChallenge, EmailChallengeStore

_FLOW_LIFETIME = timedelta(minutes=5)
_STATE_PREFIX = "gha_"
_REPLAY_SENTINEL = "github-web-oauth@internal.invalid"
_AUTHORIZATION_ENDPOINT = "https://github.com/login/oauth/authorize"
_TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
_USER_ENDPOINT = "https://api.github.com/user"
_EMAILS_ENDPOINT = "https://api.github.com/user/emails"
_API_VERSION = "2022-11-28"


class GitHubWebOAuthError(PermissionError):
    """GitHub Web OAuth evidence is missing, stale, replayed, or invalid."""


class GitHubWebOAuthStateError(GitHubWebOAuthError):
    """OAuth state is malformed, expired, replayed, or invalid."""


class GitHubWebOAuthTokenExchangeError(GitHubWebOAuthError):
    """GitHub token endpoint did not return an acceptable response."""


class GitHubWebOAuthIdentityError(GitHubWebOAuthError):
    """GitHub account evidence could not be verified."""


@dataclass(frozen=True, slots=True)
class GitHubWebOAuthCredentials:
    client_id: str
    client_secret: str
    state_secret: str

    @classmethod
    def from_environment_optional(
        cls, env: Mapping[str, str]
    ) -> GitHubWebOAuthCredentials | None:
        keys = (
            "ILAIOS_GITHUB_WEB_CLIENT_ID",
            "ILAIOS_GITHUB_WEB_CLIENT_SECRET",
            "ILAIOS_GITHUB_WEB_OAUTH_STATE_SECRET",
        )
        values = tuple(env.get(key, "").strip() for key in keys)
        if not any(values):
            return None
        if not all(values):
            raise GitHubWebOAuthError("GitHub Web OAuth configuration is incomplete")
        client_id, client_secret, state_secret = values
        if len(client_id) < 8:
            raise GitHubWebOAuthError("GitHub Web OAuth client id is invalid")
        if len(client_secret) < 16:
            raise GitHubWebOAuthError(
                "GitHub Web OAuth client secret is unavailable or too short"
            )
        if len(state_secret) < 32:
            raise GitHubWebOAuthError(
                "GitHub Web OAuth state secret is unavailable or too short"
            )
        if secrets.compare_digest(client_secret, state_secret):
            raise GitHubWebOAuthError(
                "GitHub Web OAuth state secret must differ from client secret"
            )
        return cls(client_id, client_secret, state_secret)


class GitHubWebOAuthReplayStore(Protocol):
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


class IdentityChallengeGitHubWebOAuthReplayStore:
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
            raise GitHubWebOAuthError("GitHub OAuth replay marker is invalid")
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
class GitHubWebOAuthStart:
    state: str
    authorization_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class GitHubWebOAuthCompletion:
    identity: VerifiedExternalIdentity
    purpose: str


class GitHubWebOAuthService:
    def __init__(
        self,
        *,
        credentials: GitHubWebOAuthCredentials,
        replay_store: GitHubWebOAuthReplayStore,
        request_session: requests.Session | None = None,
    ) -> None:
        self._credentials = credentials
        self._replay_store = replay_store
        self._http = request_session or requests.Session()

    def start(
        self,
        *,
        redirect_uri: str,
        now: datetime,
        purpose: str = "signin",
    ) -> GitHubWebOAuthStart:
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
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        query = urlencode(
            {
                "client_id": self._credentials.client_id,
                "redirect_uri": redirect_uri,
                "scope": "read:user user:email",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
        )
        return GitHubWebOAuthStart(
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
    ) -> GitHubWebOAuthCompletion:
        current = _utc(now)
        _validate_redirect(redirect_uri)
        challenge_id, purpose = _state_coordinates(state)
        normalized_code = _opaque(code, "authorization code")
        if not self._replay_store.consume(
            challenge_id=challenge_id,
            state_digest=_digest(state),
            now=current,
        ):
            raise GitHubWebOAuthStateError(
                "GitHub OAuth state is invalid, expired, or already used"
            )
        verifier = _derive(self._credentials.state_secret, "pkce", state, size=64)
        try:
            response = self._http.post(
                _TOKEN_ENDPOINT,
                data={
                    "client_id": self._credentials.client_id,
                    "client_secret": self._credentials.client_secret,
                    "code": normalized_code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": verifier,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
        except requests.RequestException as error:
            raise GitHubWebOAuthTokenExchangeError(
                "GitHub token exchange failed"
            ) from error
        try:
            payload = response.json()
            response.raise_for_status()
        except (ValueError, requests.RequestException) as error:
            raise GitHubWebOAuthTokenExchangeError(
                "GitHub token exchange failed"
            ) from error
        if not isinstance(payload, dict):
            raise GitHubWebOAuthTokenExchangeError(
                "GitHub token response is malformed"
            )
        access_token = payload.get("access_token")
        token_type = payload.get("token_type")
        if (
            not isinstance(access_token, str)
            or not access_token.strip()
            or not isinstance(token_type, str)
            or token_type.casefold() != "bearer"
        ):
            raise GitHubWebOAuthTokenExchangeError(
                "GitHub token response is malformed"
            )
        headers = {
            "Authorization": f"Bearer {access_token.strip()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
        }
        try:
            user_response = self._http.get(_USER_ENDPOINT, headers=headers, timeout=10)
            user = user_response.json()
            user_response.raise_for_status()
        except (ValueError, requests.RequestException) as error:
            raise GitHubWebOAuthIdentityError(
                "GitHub user verification failed"
            ) from error
        if not isinstance(user, dict):
            raise GitHubWebOAuthIdentityError("GitHub user response is malformed")
        user_id = user.get("id")
        if not isinstance(user_id, int) or user_id <= 0:
            raise GitHubWebOAuthIdentityError("GitHub user id is invalid")

        verified_email: str | None = None
        try:
            email_response = self._http.get(
                _EMAILS_ENDPOINT, headers=headers, timeout=10
            )
            emails = email_response.json()
            email_response.raise_for_status()
        except (ValueError, requests.RequestException):
            emails = []
        if isinstance(emails, list):
            for item in emails:
                if (
                    isinstance(item, dict)
                    and item.get("primary") is True
                    and item.get("verified") is True
                    and isinstance(item.get("email"), str)
                ):
                    candidate = item["email"].strip().casefold()
                    if candidate:
                        verified_email = candidate
                        break
        identity = VerifiedExternalIdentity(
            provider=IdentityProvider.GITHUB,
            subject=str(user_id),
            email=verified_email,
            email_verified=verified_email is not None,
        ).normalized()
        return GitHubWebOAuthCompletion(identity=identity, purpose=purpose)


def _state_coordinates(state: str) -> tuple[str, str]:
    normalized = _opaque(state, "state")
    parts = normalized.split(".", 2)
    if len(parts) != 3 or not parts[0].startswith(_STATE_PREFIX):
        raise GitHubWebOAuthStateError("GitHub OAuth state format is invalid")
    if len(parts[0]) != len(_STATE_PREFIX) + 32 or len(parts[2]) < 32:
        raise GitHubWebOAuthStateError("GitHub OAuth state format is invalid")
    purpose = {"s": "signin", "l": "link"}.get(parts[1])
    if purpose is None:
        raise GitHubWebOAuthStateError("GitHub OAuth state purpose is invalid")
    return parts[0], purpose


def _purpose_marker(purpose: str) -> str:
    marker = {"signin": "s", "link": "l"}.get(purpose)
    if marker is None:
        raise GitHubWebOAuthError("GitHub OAuth purpose is invalid")
    return marker


def _validate_redirect(value: str) -> None:
    if value != "https://app.ilaios.com/auth/github/callback":
        raise GitHubWebOAuthError("GitHub Web OAuth redirect URI is invalid")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _derive(secret: str, purpose: str, state: str, *, size: int) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{purpose}\0{state}".encode("utf-8"),
        hashlib.sha512,
    ).digest()
    return _base64url(digest)[:size]


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _opaque(value: str, field: str) -> str:
    normalized = value.strip()
    if normalized != value or not 8 <= len(normalized) <= 4096:
        raise GitHubWebOAuthError(f"GitHub {field} is invalid")
    if any(character.isspace() or ord(character) < 0x20 for character in normalized):
        raise GitHubWebOAuthError(f"GitHub {field} is invalid")
    return normalized


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise GitHubWebOAuthError("GitHub OAuth timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "GitHubWebOAuthCompletion",
    "GitHubWebOAuthCredentials",
    "GitHubWebOAuthError",
    "GitHubWebOAuthIdentityError",
    "GitHubWebOAuthService",
    "GitHubWebOAuthStart",
    "GitHubWebOAuthStateError",
    "GitHubWebOAuthTokenExchangeError",
    "IdentityChallengeGitHubWebOAuthReplayStore",
]
