from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.central_identity import IdentityProvider
from services.email_auth import (
    EmailAuthError,
    EmailAuthService,
    InMemoryEmailChallengeStore,
)

NOW = datetime(2026, 8, 23, 18, 0, tzinfo=timezone.utc)


def _service(*, max_issues: int = 5) -> EmailAuthService:
    return EmailAuthService(
        InMemoryEmailChallengeStore(),
        ttl=timedelta(minutes=10),
        rate_window=timedelta(minutes=15),
        max_issues_per_window=max_issues,
    )


def test_verified_email_challenge_produces_canonical_email_identity() -> None:
    service = _service()
    issued = service.issue(" User@Example.COM ", now=NOW)

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email="user@example.com",
        secret=issued.secret,
        now=NOW + timedelta(minutes=1),
    )

    assert identity.provider is IdentityProvider.EMAIL
    assert identity.subject == "user@example.com"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.key() == (IdentityProvider.EMAIL, "", "user@example.com")


def test_email_challenge_is_single_use_and_replay_fails_closed() -> None:
    service = _service()
    issued = service.issue("user@example.com", now=NOW)

    service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=1),
    )

    with pytest.raises(EmailAuthError, match="invalid, expired, or already used"):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret=issued.secret,
            now=NOW + timedelta(minutes=2),
        )


def test_email_challenge_rejects_wrong_email_without_consuming_secret() -> None:
    service = _service()
    issued = service.issue("owner@example.com", now=NOW)

    with pytest.raises(EmailAuthError):
        service.verify(
            challenge_id=issued.challenge_id,
            email="attacker@example.com",
            secret=issued.secret,
            now=NOW + timedelta(minutes=1),
        )

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=2),
    )
    assert identity.subject == "owner@example.com"


def test_email_challenge_rejects_wrong_secret_without_consuming_challenge() -> None:
    service = _service()
    issued = service.issue("owner@example.com", now=NOW)

    with pytest.raises(EmailAuthError):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret="x" * 48,
            now=NOW + timedelta(minutes=1),
        )

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=2),
    )
    assert identity.email_verified is True


def test_email_challenge_expires_fail_closed() -> None:
    service = _service()
    issued = service.issue("user@example.com", now=NOW)

    with pytest.raises(EmailAuthError, match="invalid, expired, or already used"):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret=issued.secret,
            now=NOW + timedelta(minutes=10),
        )


def test_email_challenge_rate_limit_is_per_normalized_email() -> None:
    service = _service(max_issues=2)
    service.issue("User@Example.com", now=NOW)
    service.issue("user@example.COM", now=NOW + timedelta(minutes=1))

    with pytest.raises(EmailAuthError, match="rate limit"):
        service.issue(" USER@example.com ", now=NOW + timedelta(minutes=2))

    other = service.issue("other@example.com", now=NOW + timedelta(minutes=2))
    assert other.email == "other@example.com"


def test_email_challenge_rate_window_recovers_without_disabling_limits() -> None:
    service = _service(max_issues=1)
    service.issue("user@example.com", now=NOW)

    with pytest.raises(EmailAuthError, match="rate limit"):
        service.issue("user@example.com", now=NOW + timedelta(minutes=14))

    issued = service.issue("user@example.com", now=NOW + timedelta(minutes=16))
    assert issued.email == "user@example.com"


def test_email_challenge_rejects_malformed_email() -> None:
    malformed_emails = (
        "",
        "missing-at.example.com",
        "@example.com",
        "user@localhost",
        "a b@example.com",
    )
    for email in malformed_emails:
        with pytest.raises(EmailAuthError, match="email address is invalid"):
            _service().issue(email, now=NOW)


def test_email_auth_rejects_naive_clock_input() -> None:
    with pytest.raises(EmailAuthError, match="timezone-aware"):
        _service().issue("user@example.com", now=datetime(2026, 8, 23, 18, 0))
