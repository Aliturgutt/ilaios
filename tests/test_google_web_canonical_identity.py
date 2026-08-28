from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.central_identity import (
    CentralIdentityService,
    IdentityProvider,
    InMemoryCentralIdentityStore,
    VerifiedExternalIdentity,
)
from services.google_web_canonical_identity import (
    GoogleWebCanonicalIdentityError,
    GoogleWebCanonicalIdentityFlow,
)

_NOW = datetime(2026, 8, 29, tzinfo=timezone.utc)


class _OAuth:
    def __init__(self, identity: VerifiedExternalIdentity) -> None:
        self.identity = identity
        self.calls: list[tuple[str, str, datetime]] = []

    def complete(
        self, *, state: str, code: str, now: datetime
    ) -> VerifiedExternalIdentity:
        self.calls.append((state, code, now))
        return self.identity


def _google(subject: str = "google-subject-123") -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject=subject,
        email="user@example.com",
        email_verified=True,
    )


def test_verified_google_subject_resolves_stable_canonical_user_and_tenant() -> None:
    store = InMemoryCentralIdentityStore()
    oauth = _OAuth(_google())
    flow = GoogleWebCanonicalIdentityFlow(
        oauth=oauth,  # type: ignore[arg-type]
        identity=CentralIdentityService(store),
    )

    first = flow.complete(state="state-value-12345", code="code-value-123456", now=_NOW)
    second = flow.complete(state="state-value-67890", code="code-value-654321", now=_NOW)

    assert first == second
    assert first.user_id.startswith("usr_")
    assert first.tenant_id.startswith("tnt_")
    assert len(store.list_links(first.user_id)) == 1


def test_distinct_immutable_google_subjects_cannot_collapse_by_email() -> None:
    store = InMemoryCentralIdentityStore()
    service = CentralIdentityService(store)
    first = GoogleWebCanonicalIdentityFlow(
        oauth=_OAuth(_google("google-subject-one")),  # type: ignore[arg-type]
        identity=service,
    ).complete(state="state-value-12345", code="code-value-123456", now=_NOW)
    second = GoogleWebCanonicalIdentityFlow(
        oauth=_OAuth(_google("google-subject-two")),  # type: ignore[arg-type]
        identity=service,
    ).complete(state="state-value-67890", code="code-value-654321", now=_NOW)

    assert first.user_id != second.user_id
    assert first.tenant_id != second.tenant_id


def test_caller_cannot_select_canonical_user_or_tenant() -> None:
    flow = GoogleWebCanonicalIdentityFlow(
        oauth=_OAuth(_google()),  # type: ignore[arg-type]
        identity=CentralIdentityService(InMemoryCentralIdentityStore()),
    )

    with pytest.raises(TypeError):
        flow.complete(  # type: ignore[call-arg]
            state="state-value-12345",
            code="code-value-123456",
            now=_NOW,
            user_id="attacker-user",
            tenant_id="attacker-tenant",
        )


def test_non_google_provider_evidence_fails_closed() -> None:
    flow = GoogleWebCanonicalIdentityFlow(
        oauth=_OAuth(
            VerifiedExternalIdentity(
                provider=IdentityProvider.GITHUB,
                subject="github-subject",
            )
        ),  # type: ignore[arg-type]
        identity=CentralIdentityService(InMemoryCentralIdentityStore()),
    )

    with pytest.raises(GoogleWebCanonicalIdentityError):
        flow.complete(state="state-value-12345", code="code-value-123456", now=_NOW)
