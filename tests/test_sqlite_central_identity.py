from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.control_plane.migrations import migrate_database
from services.sqlite_central_identity import SQLiteCentralIdentityStore


def _identity(
    provider: IdentityProvider,
    subject: str,
    *,
    email: str | None = None,
    verified: bool = False,
) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=verified,
    )


def _service(database: Path) -> tuple[CentralIdentityService, sqlite3.Connection]:
    connection = sqlite3.connect(database)
    return CentralIdentityService(SQLiteCentralIdentityStore(connection)), connection


def test_identity_survives_process_restart(tmp_path: Path) -> None:
    database = tmp_path / "control-plane.db"
    migrate_database(database)
    service, connection = _service(database)
    identity = _identity(
        IdentityProvider.GOOGLE,
        "google-sub-stable",
        email="Person@Example.com",
        verified=True,
    )
    first = service.sign_in(identity)
    connection.close()

    restarted, restarted_connection = _service(database)
    try:
        assert restarted.sign_in(identity) == first
    finally:
        restarted_connection.close()


def test_same_verified_email_different_subject_does_not_alias(tmp_path: Path) -> None:
    database = tmp_path / "control-plane.db"
    migrate_database(database)
    service, connection = _service(database)
    try:
        first = service.sign_in(
            _identity(
                IdentityProvider.GOOGLE,
                "google-sub-1",
                email="person@example.com",
                verified=True,
            )
        )
        second = service.sign_in(
            _identity(
                IdentityProvider.GOOGLE,
                "google-sub-2",
                email="person@example.com",
                verified=True,
            )
        )
        assert first.user_id != second.user_id
        assert first.tenant_id != second.tenant_id
    finally:
        connection.close()


def test_new_account_creates_server_authoritative_primary_owner_membership(tmp_path: Path) -> None:
    database = tmp_path / "control-plane.db"
    migrate_database(database)
    service, connection = _service(database)
    try:
        account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
        row = connection.execute(
            "SELECT role, status, is_primary FROM identity_memberships WHERE tenant_id = ? AND user_id = ?",
            (account.tenant_id, account.user_id),
        ).fetchone()
        assert row == ("OWNER", "ACTIVE", 1)
    finally:
        connection.close()


def test_cross_tenant_link_substitution_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "control-plane.db"
    migrate_database(database)
    service, connection = _service(database)
    try:
        first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
        second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-2"))
        github = _identity(IdentityProvider.GITHUB, "github-sub-1")
        service.link_identity(
            authenticated_user_id=first.user_id,
            authenticated_tenant_id=first.tenant_id,
            identity=github,
            recent_authentication_verified=True,
        )
        with pytest.raises(CentralIdentityError, match="already linked to another account"):
            service.link_identity(
                authenticated_user_id=second.user_id,
                authenticated_tenant_id=second.tenant_id,
                identity=github,
                recent_authentication_verified=True,
            )
    finally:
        connection.close()


def test_last_sign_in_method_cannot_be_removed_after_restart(tmp_path: Path) -> None:
    database = tmp_path / "control-plane.db"
    migrate_database(database)
    service, connection = _service(database)
    google = _identity(IdentityProvider.GOOGLE, "google-sub-1")
    account = service.sign_in(google)
    connection.close()

    restarted, restarted_connection = _service(database)
    try:
        with pytest.raises(CentralIdentityError, match="last usable sign-in method"):
            restarted.unlink_identity(
                authenticated_user_id=account.user_id,
                authenticated_tenant_id=account.tenant_id,
                identity=google,
                recent_authentication_verified=True,
            )
    finally:
        restarted_connection.close()
