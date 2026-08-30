from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from services.central_identity import IdentityProvider, VerifiedExternalIdentity
from services.github_web_oauth import (
    GitHubWebOAuthCredentials,
    GitHubWebOAuthService,
    GitHubWebOAuthStateError,
)
from services.microsoft_web_oauth import (
    MicrosoftWebOAuthCredentials,
    MicrosoftWebOAuthService,
    MicrosoftWebOAuthStateError,
)

_NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class _ReplayStore:
    def __init__(self) -> None:
        self.entries: dict[str, tuple[str, datetime]] = {}

    def put(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> None:
        assert issued_at < expires_at
        self.entries[challenge_id] = (state_digest, expires_at)

    def consume(
        self,
        *,
        challenge_id: str,
        state_digest: str,
        now: datetime,
    ) -> bool:
        entry = self.entries.pop(challenge_id, None)
        return entry is not None and entry[0] == state_digest and entry[1] > now


class _Response:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("request failed")


class _MicrosoftHTTP:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def post(
        self,
        url: str,
        *,
        data: dict[str, object],
        headers: dict[str, str],
        timeout: int,
    ) -> _Response:
        assert timeout == 10
        self.posts.append((url, data, headers))
        return _Response({"id_token": "test-microsoft-id-token"})


class _MicrosoftVerifier:
    def __init__(self, expected_nonce: str) -> None:
        self.expected_nonce = expected_nonce

    def verify(self, encoded_token: str) -> VerifiedExternalIdentity:
        assert encoded_token == "test-microsoft-id-token"
        assert len(self.expected_nonce) >= 32
        return VerifiedExternalIdentity(
            provider=IdentityProvider.MICROSOFT,
            subject="11111111-2222-3333-4444-555555555555",
            issuer=(
                "https://login.microsoftonline.com/"
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/v2.0"
            ),
        )


class _GitHubHTTP:
    def __init__(self) -> None:
        self.authorization_headers: list[str] = []

    def post(
        self,
        url: str,
        *,
        data: dict[str, object],
        headers: dict[str, str],
        timeout: int,
    ) -> _Response:
        assert url == "https://github.com/login/oauth/access_token"
        assert timeout == 10
        assert data["code_verifier"]
        return _Response({"access_token": "test-access-token", "token_type": "bearer"})

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> _Response:
        assert timeout == 10
        self.authorization_headers.append(headers["Authorization"])
        if url == "https://api.github.com/user":
            return _Response({"id": 123456789, "login": "example"})
        if url == "https://api.github.com/user/emails":
            return _Response(
                [
                    {
                        "email": "Owner@Example.com",
                        "primary": True,
                        "verified": True,
                    }
                ]
            )
        raise AssertionError(f"unexpected GitHub URL: {url}")


def test_optional_provider_credentials_are_fail_closed() -> None:
    assert MicrosoftWebOAuthCredentials.from_environment_optional({}) is None
    assert GitHubWebOAuthCredentials.from_environment_optional({}) is None

    with pytest.raises(Exception):
        MicrosoftWebOAuthCredentials.from_environment_optional(
            {"ILAIOS_MICROSOFT_WEB_CLIENT_ID": "11111111-2222-3333-4444-555555555555"}
        )
    with pytest.raises(Exception):
        GitHubWebOAuthCredentials.from_environment_optional(
            {"ILAIOS_GITHUB_WEB_CLIENT_ID": "github-client"}
        )


def test_microsoft_web_oauth_uses_pkce_state_and_preserves_flow_purpose() -> None:
    replay = _ReplayStore()
    http = _MicrosoftHTTP()
    credentials = MicrosoftWebOAuthCredentials(
        client_id="11111111-2222-3333-4444-555555555555",
        client_secret="x" * 20,
        state_secret="y" * 40,
    )
    service = MicrosoftWebOAuthService(
        credentials=credentials,
        replay_store=replay,
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda nonce, _current: _MicrosoftVerifier(nonce),
    )
    callback = "https://app.ilaios.com/auth/microsoft/callback"

    started = service.start(
        redirect_uri=callback,
        now=_NOW,
        purpose="link",
    )
    parsed = urlsplit(started.authorization_url)
    query = parse_qs(parsed.query)
    assert parsed.hostname == "login.microsoftonline.com"
    assert query["redirect_uri"] == [callback]
    assert query["code_challenge_method"] == ["S256"]
    assert query["nonce"]
    assert query["state"] == [started.state]

    completed = service.complete(
        state=started.state,
        code="test-authorization-code",
        redirect_uri=callback,
        now=_NOW + timedelta(seconds=1),
    )
    assert completed.purpose == "link"
    assert completed.identity.provider is IdentityProvider.MICROSOFT
    assert completed.identity.subject == "11111111-2222-3333-4444-555555555555"
    assert http.posts[0][1]["client_secret"] == credentials.client_secret
    assert http.posts[0][1]["code_verifier"]

    with pytest.raises(MicrosoftWebOAuthStateError):
        service.complete(
            state=started.state,
            code="test-authorization-code",
            redirect_uri=callback,
            now=_NOW + timedelta(seconds=2),
        )


def test_github_web_oauth_uses_pkce_and_verified_immutable_user_id() -> None:
    replay = _ReplayStore()
    http = _GitHubHTTP()
    credentials = GitHubWebOAuthCredentials(
        client_id="github-client-id",
        client_secret="x" * 20,
        state_secret="y" * 40,
    )
    service = GitHubWebOAuthService(
        credentials=credentials,
        replay_store=replay,
        request_session=http,  # type: ignore[arg-type]
    )
    callback = "https://app.ilaios.com/auth/github/callback"

    started = service.start(
        redirect_uri=callback,
        now=_NOW,
        purpose="signin",
    )
    parsed = urlsplit(started.authorization_url)
    query = parse_qs(parsed.query)
    assert parsed.hostname == "github.com"
    assert query["redirect_uri"] == [callback]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["read:user user:email"]

    completed = service.complete(
        state=started.state,
        code="test-authorization-code",
        redirect_uri=callback,
        now=_NOW + timedelta(seconds=1),
    )
    assert completed.purpose == "signin"
    assert completed.identity.provider is IdentityProvider.GITHUB
    assert completed.identity.subject == "123456789"
    assert completed.identity.email == "owner@example.com"
    assert completed.identity.email_verified is True
    assert http.authorization_headers == [
        "Bearer test-access-token",
        "Bearer test-access-token",
    ]

    with pytest.raises(GitHubWebOAuthStateError):
        service.complete(
            state=started.state,
            code="test-authorization-code",
            redirect_uri=callback,
            now=_NOW + timedelta(seconds=2),
        )
