from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.canonical_identity_principal import (
    CanonicalIdentityPrincipalError,
    CanonicalIdentityPrincipalResolver,
)
from services.central_identity import (
    CanonicalAccount,
    CentralIdentityService,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.control_plane.migrations import migrate_database
from services.identity import IdentityKind
from services.sqlite_central_identity import SQLiteCentralIdentityStore


def _account(database: Path) -> CanonicalAccount:
    migrate_database(database)
    connection = sqlite3.connect(database)
    try:
        identity = CentralIdentityService(SQLiteCentralIdentityStore(connection))
        return identity.sign_in(
            VerifiedExternalIdentity(
                provider=IdentityProvider.GOOGLE,
                subject="immutable-google-subject",
                email="owner@example.com",
                email_verified=True,
            )
        )
    finally:
        connection.close()


def test_resolves_server_authoritative_primary_membership_role(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)

    principal = CanonicalIdentityPrincipalResolver(database).resolve(account)

    assert principal.principal_id == account.user_id
    assert principal.tenant_id == account.tenant_id
    assert principal.kind is IdentityKind.HUMAN
    assert principal.roles == frozenset({"OWNER"})
    assert principal.attributes == frozenset()
    assert principal.authentication_methods == frozenset()


def test_rejects_caller_substituted_tenant(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    substituted = CanonicalAccount(
        user_id=account.user_id,
        tenant_id="tnt_attacker_selected",
        enabled=True,
    )

    with pytest.raises(
        CanonicalIdentityPrincipalError,
        match="primary membership is missing or ambiguous",
    ):
        CanonicalIdentityPrincipalResolver(database).resolve(substituted)


def test_rejects_disabled_canonical_user_even_with_active_membership(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_users SET enabled = 0 WHERE user_id = ?",
            (account.user_id,),
        )
        connection.commit()

    with pytest.raises(
        CanonicalIdentityPrincipalError,
        match="primary membership is not active",
    ):
        CanonicalIdentityPrincipalResolver(database).resolve(account)


def test_rejects_suspended_membership_and_blank_role(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    resolver = CanonicalIdentityPrincipalResolver(database)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status = 'SUSPENDED' WHERE user_id = ?",
            (account.user_id,),
        )
        connection.commit()

    with pytest.raises(
        CanonicalIdentityPrincipalError,
        match="primary membership is not active",
    ):
        resolver.resolve(account)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status = 'ACTIVE', role = '' WHERE user_id = ?",
            (account.user_id,),
        )
        connection.commit()

    with pytest.raises(
        CanonicalIdentityPrincipalError,
        match="primary membership is not active",
    ):
        resolver.resolve(account)
