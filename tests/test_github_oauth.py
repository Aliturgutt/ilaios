from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from services.central_identity import IdentityProvider
from services.github_oauth import (
    GITHUB_AUTHORIZATION_ENDPOINT,
    GITHUB_EMAILS_ENDPOINT,
    GITHUB_TOKEN_ENDPOINT,
    GITHUB_USER_ENDPOINT,
    GitHubOAuthEnvironment,
    GitHubOAuthError,
    GitHubOAuthService,
)

NOW = datetime(2026, 8, 22, 16, 0, tzinfo=timezone.utc)


def _environment() -> GitHubOAuthEnvironment:
    return GitHubOAuthEnvironment.from_environment(
        {
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID": "github-prod-client",
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET": "github-prod-secret",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID": "github-dev-client",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET": "github-dev-secret",
            "ILAIOS_GITHUB_PRODUCTION_REDIRECTS": (
                "https://app.ilaios.com/auth/github/callback,"
                "https://ilaios.com/auth/github/callback"
            ),
        }
    )


class _Response:
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class _Session:
    def __init__(
        self,
        *,
        token_payload: object | None = None,
        user_payload: object | None = None,
        emails_payload: object | None = None,
    ) -> None:
        self.token_payload = token_payload or {
            "access_token": "provider-access-token",
            "token_type": "bearer",
        }
        self.user_payload = user_payload or {
            "id": 98952443,
            "login": "mutable-login",
            "email": "untrusted@example.com",
        }
        self.emails_payload = emails_payload or [
            {"email": "Primary@Example.com", "primary": True, "verified": True}
        ]
        self.posts: list[tuple[str, object, object, int]] = []
        self.gets: list[tuple[str, object, int]] = []

    def post(self, url: str, *, data: object, headers: object, timeout: int) -> _Response:
        self.posts.append((url, data, headers, timeout))
        return _Response(self.token_payload)

    def get(self, url: str, *, headers: object, timeout: int) -> _Response:
        self.gets.append((url, headers, timeout))
        if url == GITHUB_USER_ENDPOINT:
            return _Response(self.user_payload)
        if url == GITHUB_EMAILS_ENDPOINT:
            return _Response(self.emails_payload)
        raise AssertionError(f"unexpected GET {url}")


def test_environment_requires_distinct_production_and_development_clients() -> None:
    env = {
        "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID": "same-client",
        "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET": "prod-secret",
        "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID": "same-client",
        "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET": "dev-secret",
        "ILAIOS_GITHUB_PRODUCTION_REDIRECTS": "https://app.ilaios.com/auth/github/callback",
    }
    with pytest.raises(GitHubOAuthError, match="clients must be distinct"):
        GitHubOAuthEnvironment.from_environment(env)


def test_environment_rejects_shared_client_secret() -> None:
    env = {
        "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID": "prod",
        "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET": "same-secret",
        "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID": "dev",
        "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET": "same-secret",
        "ILAIOS_GITHUB_PRODUCTION_REDIRECTS": "https://app.ilaios.com/auth/github/callback",
    }
    with pytest.raises(GitHubOAuthError, match="secrets must be distinct"):
        GitHubOAuthEnvironment.from_environment(env)


def test_production_redirects_fail_closed_for_http_loopback_and_userinfo() -> None:
    unsafe = (
        "http://app.ilaios.com/auth/github/callback",
        "https://127.0.0.1/auth/github/callback",
        "https://user:pass@app.ilaios.com/auth/github/callback",
    )
    for redirect in unsafe:
        env = {
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID": "prod",
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET": "prod-secret",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID": "dev",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET": "dev-secret",
            "ILAIOS_GITHUB_PRODUCTION_REDIRECTS": redirect,
        }
        with pytest.raises(GitHubOAuthError):
            GitHubOAuthEnvironment.from_environment(env)


def test_start_binds_exact_redirect_state_and_minimum_identity_scopes() -> None:
    service = GitHubOAuthService(_environment(), request_session=_Session())
    redirect = "https://app.ilaios.com/auth/github/callback"
    start = service.start(redirect, NOW)
    parsed = urlparse(start.authorization_url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == GITHUB_AUTHORIZATION_ENDPOINT
    assert query["client_id"] == ["github-prod-client"]
    assert query["redirect_uri"] == [redirect]
    assert query["state"] == [start.state]
    assert query["scope"] == ["read:user user:email"]
    assert start.expires_at == NOW + timedelta(minutes=5)


def test_start_rejects_non_allowlisted_redirect() -> None:
    service = GitHubOAuthService(_environment(), request_session=_Session())
    with pytest.raises(GitHubOAuthError, match="not allowlisted"):
        service.start("https://attacker.example/callback", NOW)


def test_complete_uses_numeric_github_user_id_not_login_or_email_as_subject() -> None:
    session = _Session(
        user_payload={"id": 98952443, "login": "renameable-handle", "email": "mutable-profile@example.com"},
        emails_payload=[
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "Primary@Example.com", "primary": True, "verified": True},
        ],
    )
    service = GitHubOAuthService(_environment(), request_session=session)
    start = service.start("https://app.ilaios.com/auth/github/callback", NOW)
    identity = service.complete(state=start.state, code="oauth-code", now=NOW)
    assert identity.provider is IdentityProvider.GITHUB
    assert identity.subject == "98952443"
    assert identity.email == "primary@example.com"
    assert identity.email_verified is True
    assert identity.key() == (IdentityProvider.GITHUB, "", "98952443")
    assert session.posts[0][0] == GITHUB_TOKEN_ENDPOINT
    assert [item[0] for item in session.gets] == [GITHUB_USER_ENDPOINT, GITHUB_EMAILS_ENDPOINT]


def test_unverified_email_is_metadata_rejected_not_identity_key() -> None:
    session = _Session(emails_payload=[{"email": "attacker@example.com", "primary": True, "verified": False}])
    service = GitHubOAuthService(_environment(), request_session=session)
    start = service.start("https://app.ilaios.com/auth/github/callback", NOW)
    identity = service.complete(state=start.state, code="oauth-code", now=NOW)
    assert identity.subject == "98952443"
    assert identity.email is None
    assert identity.email_verified is False


def test_state_is_one_use_and_replay_fails_closed() -> None:
    service = GitHubOAuthService(_environment(), request_session=_Session())
    start = service.start("https://app.ilaios.com/auth/github/callback", NOW)
    service.complete(state=start.state, code="oauth-code", now=NOW)
    with pytest.raises(GitHubOAuthError, match="state is invalid or expired"):
        service.complete(state=start.state, code="replayed-code", now=NOW)


def test_expired_state_fails_closed_before_provider_call() -> None:
    session = _Session()
    service = GitHubOAuthService(_environment(), request_session=session)
    start = service.start("https://app.ilaios.com/auth/github/callback", NOW)
    with pytest.raises(GitHubOAuthError, match="state is invalid or expired"):
        service.complete(state=start.state, code="oauth-code", now=NOW + timedelta(minutes=6))
    assert session.posts == []
    assert session.gets == []


def test_invalid_or_boolean_github_user_id_fails_closed() -> None:
    for value in (0, -1, True, "98952443"):
        service = GitHubOAuthService(_environment(), request_session=_Session(user_payload={"id": value, "login": "user"}))
        start = service.start("https://app.ilaios.com/auth/github/callback", NOW)
        with pytest.raises(GitHubOAuthError, match="invalid immutable user ID"):
            service.complete(state=start.state, code="oauth-code", now=NOW)
