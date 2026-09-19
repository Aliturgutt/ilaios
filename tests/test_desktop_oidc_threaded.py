from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest

from services.desktop_oidc import (
    DesktopAuthStatus,
    DesktopIdentityError,
    OIDCProviderConfig,
)
from services.desktop_oidc_threaded import DesktopOIDCService
from services.identity import IdentityKind, VerifiedOIDCClaims


NOW = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)


def _provider() -> OIDCProviderConfig:
    return OIDCProviderConfig(
        provider_id="google",
        display_name="Google",
        issuer="https://accounts.example.test",
        authorization_endpoint="https://accounts.example.test/authorize",
        token_endpoint="https://accounts.example.test/token",
        jwks_uri="https://accounts.example.test/jwks",
        client_id="desktop-client-id",
    )


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"id_token": "signed-id-token"}


class _BlockingHTTP:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.post_count = 0

    def post(self, url: str, **kwargs: object) -> _Response:
        del url, kwargs
        self.post_count += 1
        self.started.set()
        if not self.release.wait(timeout=5):
            raise AssertionError("test token exchange was not released")
        return _Response()


class _Verifier:
    def __init__(self, provider: OIDCProviderConfig, nonce: str) -> None:
        self.provider = provider
        self.nonce = nonce
        self.verified_expires_at = NOW + timedelta(minutes=30)

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "signed-id-token"
        return VerifiedOIDCClaims(
            issuer=self.provider.issuer,
            audience=self.provider.client_id,
            subject="user-123",
            tenant_id="tenant-123",
            expires_at=self.verified_expires_at,
            issued_at=NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset({("verified_email", "user@example.test")}),
            authentication_methods=frozenset({"pwd"}),
        )


class _FailingVerifier(_Verifier):
    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        del encoded_token
        raise DesktopIdentityError("OIDC ID token verification failed")


class _PolicyFailingVerifier(_Verifier):
    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "signed-id-token"
        return VerifiedOIDCClaims(
            issuer=self.provider.issuer,
            audience=self.provider.client_id,
            subject="user-123",
            tenant_id="tenant-123",
            expires_at=self.verified_expires_at,
            issued_at=NOW + timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"user"}),
            attributes=frozenset({("verified_email", "user@example.test")}),
            authentication_methods=frozenset({"pwd"}),
        )


def _service(http: _BlockingHTTP) -> DesktopOIDCService:
    return DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _Verifier(provider, nonce),
    )


def test_status_stays_pending_while_callback_completes_on_another_thread() -> None:
    http = _BlockingHTTP()
    service = _service(http)
    started = service.start(
        "google",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )

    completed: list[DesktopAuthStatus] = []
    failures: list[BaseException] = []

    def finish_callback() -> None:
        try:
            completed.append(
                service.complete(started.state, "authorization-code", now=NOW)
            )
        except BaseException as error:  # pragma: no cover - asserted below
            failures.append(error)

    thread = threading.Thread(target=finish_callback)
    thread.start()
    assert http.started.wait(timeout=2)

    pending = service.status(started.state, now=NOW)
    assert pending.status == "pending"
    assert pending.provider_id == "google"

    http.release.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert failures == []
    assert len(completed) == 1
    authenticated = service.status(started.state, now=NOW)
    assert authenticated.status == "authenticated"
    assert authenticated.session_id is not None


def test_duplicate_callback_does_not_consume_state_or_clear_inflight_marker() -> None:
    http = _BlockingHTTP()
    service = _service(http)
    started = service.start(
        "google",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )

    completed: list[DesktopAuthStatus] = []
    failures: list[BaseException] = []

    def finish_callback(code: str) -> None:
        try:
            completed.append(service.complete(started.state, code, now=NOW))
        except BaseException as error:  # pragma: no cover - asserted below
            failures.append(error)

    first = threading.Thread(target=finish_callback, args=("authorization-code",))
    duplicate = threading.Thread(target=finish_callback, args=("duplicate-code",))

    first.start()
    assert http.started.wait(timeout=2)

    duplicate.start()

    pending = service.status(started.state, now=NOW)
    assert pending.status == "pending"
    assert pending.provider_id == "google"

    http.release.set()
    first.join(timeout=5)
    duplicate.join(timeout=5)

    assert not first.is_alive()
    assert not duplicate.is_alive()
    assert failures == []
    assert len(completed) == 2
    assert completed[0].status == "authenticated"
    assert completed[1] == completed[0]
    assert http.post_count == 1

    authenticated = service.status(started.state, now=NOW)
    assert authenticated.status == "authenticated"
    assert authenticated.session_id == completed[0].session_id


def test_first_callback_failure_is_not_masked_by_duplicate_callback() -> None:
    http = _BlockingHTTP()
    service = DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _FailingVerifier(provider, nonce),
    )
    started = service.start(
        "google",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )

    first_error: list[BaseException] = []

    def finish_first_callback() -> None:
        try:
            service.complete(started.state, "authorization-code", now=NOW)
        except BaseException as error:  # pragma: no cover - asserted below
            first_error.append(error)

    first = threading.Thread(target=finish_first_callback)
    first.start()
    assert http.started.wait(timeout=2)
    http.release.set()
    first.join(timeout=5)

    assert not first.is_alive()
    assert len(first_error) == 1
    assert str(first_error[0]) == "OIDC ID token verification failed"

    with pytest.raises(
        DesktopIdentityError,
        match="OIDC ID token verification failed",
    ):
        service.complete(started.state, "duplicate-code", now=NOW)

    with pytest.raises(
        DesktopIdentityError,
        match="OIDC ID token verification failed",
    ):
        service.status(started.state, now=NOW)

    assert http.post_count == 1


def test_identity_policy_failure_is_converted_and_preserved_for_callback() -> None:
    http = _BlockingHTTP()
    service = DesktopOIDCService(
        (_provider(),),
        request_session=http,  # type: ignore[arg-type]
        verifier_factory=lambda provider, nonce: _PolicyFailingVerifier(
            provider, nonce
        ),
    )
    started = service.start(
        "google",
        "http://127.0.0.1:43123/oauth/callback",
        now=NOW,
    )

    http.release.set()
    with pytest.raises(
        DesktopIdentityError,
        match="OIDC identity validation failed: token is not currently valid",
    ):
        service.complete(started.state, "authorization-code", now=NOW)

    with pytest.raises(
        DesktopIdentityError,
        match="OIDC identity validation failed: token is not currently valid",
    ):
        service.complete(started.state, "duplicate-code", now=NOW)

    with pytest.raises(
        DesktopIdentityError,
        match="OIDC identity validation failed: token is not currently valid",
    ):
        service.status(started.state, now=NOW)

    assert http.post_count == 1
