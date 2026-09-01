from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.account_lifecycle import (
    AccountLifecycleService,
    SQLiteAccountLifecycleAuditStore,
    SQLiteIdentityLinkRemovalStore,
)
from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.central_identity_sqlite import SQLiteCentralIdentityStore


def _identity(
    provider: IdentityProvider,
    subject: str,
    *,
    email: str | None = None,
    verified: bool = False,
    issuer: str | None = None,
) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=verified,
        issuer=issuer,
    )


def _services(database: Path) -> tuple[CentralIdentityService, AccountLifecycleService]:
    store = SQLiteCentralIdentityStore(database)
    return (
        CentralIdentityService(store),
        AccountLifecycleService(
            identity_store=store,
            removal_store=SQLiteIdentityLinkRemovalStore(database),
            audit_store=SQLiteAccountLifecycleAuditStore(database),
        ),
    )


def _lifecycle_events(database: Path) -> list[dict[str, object]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = ? ORDER BY sequence",
            ("identity.account_lifecycle",),
        ).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def test_recovery_resolves_existing_link_without_creating_account(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    account = central.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))

    recovered = lifecycle.recover_existing_account(
        _identity(IdentityProvider.GOOGLE, "google-1")
    )

    assert recovered == account
    events = _lifecycle_events(database)
    assert events[-1]["action"] == "recover_existing_account"
    assert events[-1]["status"] == "success"
    assert events[-1]["user_id"] == account.user_id
    assert events[-1]["tenant_id"] == account.tenant_id
    assert events[-1]["provider"] == "google"
    assert "google-1" not in json.dumps(events[-1])


def test_recovery_unknown_identity_fails_closed_and_does_not_create(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    existing = central.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))

    with pytest.raises(CentralIdentityError, match="recovery identity is not linked"):
        lifecycle.recover_existing_account(
            _identity(
                IdentityProvider.GITHUB,
                "123456",
                email="same@example.com",
                verified=True,
            )
        )

    restarted = CentralIdentityService(SQLiteCentralIdentityStore(database))
    assert restarted.sign_in(_identity(IdentityProvider.GOOGLE, "google-1")) == existing
    events = _lifecycle_events(database)
    assert events[-1]["action"] == "recover_existing_account"
    assert events[-1]["status"] == "denied"
    assert events[-1]["user_id"] is None
    assert events[-1]["tenant_id"] is None
    assert "123456" not in json.dumps(events[-1])
    assert "same@example.com" not in json.dumps(events[-1])


def test_unlink_requires_distinct_linked_reauthentication(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    account = central.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))
    github = _identity(IdentityProvider.GITHUB, "123456")
    central.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )

    with pytest.raises(CentralIdentityError, match="different re-authenticated identity"):
        lifecycle.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=github,
            reauthenticated_identity=github,
        )

    with pytest.raises(CentralIdentityError, match="re-authenticated identity is not linked"):
        lifecycle.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=github,
            reauthenticated_identity=_identity(IdentityProvider.APPLE, "apple-unlinked"),
        )

    events = _lifecycle_events(database)
    assert [event["status"] for event in events[-2:]] == ["denied", "denied"]


def test_unlink_removes_only_target_and_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    google = _identity(IdentityProvider.GOOGLE, "google-1")
    github = _identity(IdentityProvider.GITHUB, "123456")
    account = central.sign_in(google)
    central.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )

    removed = lifecycle.unlink_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        reauthenticated_identity=google,
    )
    assert removed.provider is IdentityProvider.GITHUB

    restarted_store = SQLiteCentralIdentityStore(database)
    restarted = CentralIdentityService(restarted_store)
    assert restarted.sign_in(google) == account
    assert restarted_store.find_link(github) is None
    events = _lifecycle_events(database)
    assert events[-1]["action"] == "unlink_identity"
    assert events[-1]["status"] == "success"
    assert events[-1]["user_id"] == account.user_id
    assert events[-1]["tenant_id"] == account.tenant_id
    assert events[-1]["provider"] == "github"
    assert "123456" not in json.dumps(events[-1])


def test_unlink_last_usable_login_is_denied(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    google = _identity(IdentityProvider.GOOGLE, "google-1")
    account = central.sign_in(google)

    with pytest.raises(CentralIdentityError, match="different re-authenticated identity"):
        lifecycle.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=google,
            reauthenticated_identity=google,
        )

    assert _lifecycle_events(database)[-1]["status"] == "denied"


def test_cross_account_reauthentication_cannot_authorize_unlink(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    first_google = _identity(IdentityProvider.GOOGLE, "google-1")
    first_github = _identity(IdentityProvider.GITHUB, "123456")
    first = central.sign_in(first_google)
    central.link_identity(
        authenticated_user_id=first.user_id,
        authenticated_tenant_id=first.tenant_id,
        identity=first_github,
        recent_authentication_verified=True,
    )
    attacker = central.sign_in(_identity(IdentityProvider.APPLE, "apple-attacker"))

    with pytest.raises(CentralIdentityError, match="another canonical account"):
        lifecycle.unlink_identity(
            authenticated_user_id=first.user_id,
            authenticated_tenant_id=first.tenant_id,
            identity=first_github,
            reauthenticated_identity=_identity(IdentityProvider.APPLE, "apple-attacker"),
        )

    assert attacker.user_id != first.user_id
    assert _lifecycle_events(database)[-1]["status"] == "denied"


def test_verified_email_match_never_authorizes_recovery_or_unlink(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    google = _identity(
        IdentityProvider.GOOGLE,
        "google-1",
        email="person@example.com",
        verified=True,
    )
    account = central.sign_in(google)
    email_identity = _identity(
        IdentityProvider.EMAIL,
        "person@example.com",
        email="person@example.com",
        verified=True,
    )

    with pytest.raises(CentralIdentityError, match="recovery identity is not linked"):
        lifecycle.recover_existing_account(email_identity)

    assert central.sign_in(google) == account
    event = _lifecycle_events(database)[-1]
    assert event["status"] == "denied"
    assert "person@example.com" not in json.dumps(event)


def test_lifecycle_audit_survives_restart_without_raw_provider_subject(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    central, lifecycle = _services(database)
    account = central.sign_in(_identity(IdentityProvider.GOOGLE, "secret-provider-subject"))
    lifecycle.recover_existing_account(
        _identity(IdentityProvider.GOOGLE, "secret-provider-subject")
    )

    SQLiteAccountLifecycleAuditStore(database)
    events = _lifecycle_events(database)
    assert events[-1]["user_id"] == account.user_id
    assert len(str(events[-1]["identity_key_sha256"])) == 64
    assert "secret-provider-subject" not in json.dumps(events[-1])
