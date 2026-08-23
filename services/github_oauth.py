"""GitHub OAuth 2.0 boundary for canonical ILAIOS identity.

GitHub usernames and email addresses are mutable metadata. The only external
identity subject emitted by this module is the immutable numeric GitHub user ID
returned by the authenticated ``/user`` API.
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlencode, urlparse

import requests

from services.central_identity import IdentityProvider, VerifiedExternalIdentity

GITHUB_AUTHORIZATION_ENDPOINT = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
GITHUB_USER_ENDPOINT = "https://api.github.com/user"
GITHUB_EMAILS_ENDPOINT = "https://api.github.com/user/emails"
_FLOW_LIFETIME = timedelta(minutes=5)


class GitHubOAuthError(PermissionError):
    """GitHub OAuth configuration, callback, or provider evidence failed closed."""


class _HTTPResponse(Protocol):
    def json(self) -> object: ...

    def raise_for_status(self) -> None: ...


class _HTTPSession(Protocol):
    def post(
        self,
        url: str,
        *,
        data: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: int,
    ) -> _HTTPResponse: ...

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: int,
    ) -> _HTTPResponse: ...


@dataclass(frozen=True, slots=True)
class GitHubOAuthEnvironment:
    production_client_id: str
    production_client_secret: str
    development_client_id: str
    development_client_secret: str
    production_redirects: tuple[str, ...]

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> GitHubOAuthEnvironment:
        production_client_id = _required(env, "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID")
        production_client_secret = _required(
            env, "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET"
        )
        development_client_id = _required(env, "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID")
        development_client_secret = _required(
            env, "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET"
        )
        if production_client_id == development_client_id:
            raise GitHubOAuthError(
                "GitHub production and development clients must be distinct"
            )
        if production_client_secret == development_client_secret:
            raise GitHubOAuthError(
                "GitHub production and development client secrets must be distinct"
            )
        raw_redirects = _required(env, "ILAIOS_GITHUB_PRODUCTION_REDIRECTS")
        redirects = tuple(
            value.strip() for value in raw_redirects.split(",") if value.strip()
        )
        if not redirects:
            raise GitHubOAuthError("GitHub production redirect allowlist is empty")
        if len(set(redirects)) != len(redirects):
            raise GitHubOAuthError("GitHub production redirect allowlist has duplicates")
        for redirect in redirects:
            _validate_production_redirect(redirect)
        return cls(
            production_client_id=production_client_id,
            production_client_secret=production_client_secret,
            development_client_id=development_client_id,
            development_client_secret=development_client_secret,
            production_redirects=redirects,
        )

    def require_production_redirect(self, redirect_uri: str) -> str:
        redirect = redirect_uri.strip()
        if redirect not in self.production_redirects:
            raise GitHubOAuthError("GitHub production redirect URI is not allowlisted")
        return redirect


@dataclass(frozen=True, slots=True)
class GitHubAuthStart:
    state: str
    authorization_url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class _GitHubFlow:
    state: str
    redirect_uri: str
    expires_at: datetime


class GitHubOAuthService:
    """Perform server-side GitHub OAuth and emit verified canonical identity input."""

    def __init__(
        self,
        environment: GitHubOAuthEnvironment,
        *,
        request_session: _HTTPSession | None = None,
    ) -> None:
        self._environment = environment
        self._http: _HTTPSession = request_session or requests.Session()
        self._flows: dict[str, _GitHubFlow] = {}

    def start(
        self,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> GitHubAuthStart:
        current = _utc(now)
        self._purge(current)
        redirect = self._environment.require_production_redirect(redirect_uri)
        state = secrets.token_urlsafe(32)
        expires_at = current + _FLOW_LIFETIME
        self._flows[state] = _GitHubFlow(
            state=state,
            redirect_uri=redirect,
            expires_at=expires_at,
        )
        query = urlencode(
            {
                "client_id": self._environment.production_client_id,
                "redirect_uri": redirect,
                "scope": "read:user user:email",
                "state": state,
                "allow_signup": "true",
            }
        )
        return GitHubAuthStart(
            state=state,
            authorization_url=f"{GITHUB_AUTHORIZATION_ENDPOINT}?{query}",
            expires_at=expires_at,
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> VerifiedExternalIdentity:
        current = _utc(now)
        self._purge(current)
        flow = self._flows.pop(state, None)
        if flow is None or flow.expires_at <= current:
            raise GitHubOAuthError("GitHub OAuth state is invalid or expired")
        authorization_code = code.strip()
        if not authorization_code:
            raise GitHubOAuthError("GitHub authorization code is required")

        token_payload = self._post_json(
            GITHUB_TOKEN_ENDPOINT,
            data={
                "client_id": self._environment.production_client_id,
                "client_secret": self._environment.production_client_secret,
                "code": authorization_code,
                "redirect_uri": flow.redirect_uri,
            },
            headers={"Accept": "application/json"},
            failure="GitHub token exchange failed",
        )
        access_token = token_payload.get("access_token")
        token_type = token_payload.get("token_type")
        if not isinstance(access_token, str) or not access_token.strip():
            raise GitHubOAuthError("GitHub token response is missing access token")
        if not isinstance(token_type, str) or token_type.casefold() != "bearer":
            raise GitHubOAuthError("GitHub token response has unsupported token type")

        auth_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token.strip()}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        user_payload = self._get_json(
            GITHUB_USER_ENDPOINT,
            headers=auth_headers,
            failure="GitHub user lookup failed",
        )
        github_user_id = user_payload.get("id")
        if (
            not isinstance(github_user_id, int)
            or isinstance(github_user_id, bool)
            or github_user_id <= 0
        ):
            raise GitHubOAuthError("GitHub user response has invalid immutable user ID")

        email_payload = self._get_json_list(
            GITHUB_EMAILS_ENDPOINT,
            headers=auth_headers,
            failure="GitHub verified email lookup failed",
        )
        verified_email = _select_verified_email(email_payload)
        return VerifiedExternalIdentity(
            provider=IdentityProvider.GITHUB,
            subject=str(github_user_id),
            email=verified_email,
            email_verified=verified_email is not None,
        ).normalized()

    def _post_json(
        self,
        url: str,
        *,
        data: Mapping[str, str],
        headers: Mapping[str, str],
        failure: str,
    ) -> dict[str, object]:
        try:
            response = self._http.post(url, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GitHubOAuthError(failure) from error
        if not isinstance(payload, dict):
            raise GitHubOAuthError(failure)
        return payload

    def _get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        failure: str,
    ) -> dict[str, object]:
        try:
            response = self._http.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GitHubOAuthError(failure) from error
        if not isinstance(payload, dict):
            raise GitHubOAuthError(failure)
        return payload

    def _get_json_list(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        failure: str,
    ) -> list[object]:
        try:
            response = self._http.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GitHubOAuthError(failure) from error
        if not isinstance(payload, list):
            raise GitHubOAuthError(failure)
        return payload

    def _purge(self, now: datetime) -> None:
        expired = [state for state, flow in self._flows.items() if flow.expires_at <= now]
        for state in expired:
            self._flows.pop(state, None)


def _select_verified_email(items: list[object]) -> str | None:
    verified: list[tuple[bool, str]] = []
    for item in items:
        if not isinstance(item, dict) or item.get("verified") is not True:
            continue
        raw_email = item.get("email")
        if not isinstance(raw_email, str) or not raw_email.strip():
            continue
        verified.append((item.get("primary") is True, raw_email.strip().casefold()))
    if not verified:
        return None
    verified.sort(key=lambda item: (not item[0], item[1]))
    return verified[0][1]


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise GitHubOAuthError(f"{key} is required")
    return value


def _validate_production_redirect(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise GitHubOAuthError("GitHub production redirect URI must use HTTPS")
    if parsed.username or parsed.password or parsed.fragment:
        raise GitHubOAuthError("GitHub production redirect URI has forbidden components")
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise GitHubOAuthError("GitHub production redirect URI must not use loopback")


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise GitHubOAuthError("GitHub OAuth timestamps must be timezone-aware")
    return current.astimezone(timezone.utc)
