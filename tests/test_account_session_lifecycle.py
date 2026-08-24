from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.account_session_lifecycle import (
    AccountSessionLifecycleService,
    SQLiteAccountSessionAuditStore,
    SQLiteAccountSessionRevocationStore,
)
from services.central_identity import CentralIdentityError, CentralIdentityService, IdentityProvider, VerifiedExternalIdentity
from services.central_identity_sqlite import SQLiteCentralIdentityStore


def _identity(subject: str) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(provider=IdentityProvider.GOOGLE, subject=subject)


def _services(database: Path) -> tuple[SQLiteCentralIdentityStore, CentralIdentityService, AccountSessionLifecycleService]:
    store = SQLiteCentralIdentityStore(database)
    return (
        store,
        CentralIdentityService(store),
        AccountSessionLifecycleService(
            identity_store=store,
            revocation_store=SQLiteAccountSessionRevocationStore(database),
            audit_store=SQLiteAccountSessionAuditStore(database),
        ),
    )


def _persist_session(
    store: SQLiteCentralIdentityStore,
    *,
    session_id: str,
    user_id: str,
    tenant_id: str,
    credential_seed: str,
) -> None:
    import hashlib

    store.persist_session(
        session_id=session_id,
        user_id=user_id,
        tenant_id=tenant_id,
        credential_hash=hashlib.sha256(credential_seed.encode("utf-8")).hexdigest(),
        created_at="2026-08-24T08:00:00+00:00",
        expires_at="2026-08-25T08:00:00+00:00",
    )


def _events(database: Path) -> list[dict[str, object]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = ? ORDER BY sequence",
            ("identity.account_session_lifecycle",),
        ).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def test_logout_revokes_only_owned_session_and_hashes_audit_identifier(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    store, central, lifecycle = _services(database)
    account = central.sign_in(_identity("google-1"))
    _persist_session(
        store,
        session_id="session-secret-1",
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        credential_seed="credential-1",
    )
    _persist_session(
        store,
        session_id="session-secret-2",
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        credential_seed="credential-2",
    )

    assert lifecycle.logout_session(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        session_id="session-secret-1",
    ) is True

    assert store.get_session("session-secret-1") is not None
    assert store.get_session("session-secret-1").revoked_at is not None  # type: ignore[union-attr]
    assert store.get_session("session-secret-2") is not None
    assert store.get_session("session-secret-2").revoked_at is None  # type: ignore[union-attr]
    event = _events(database)[-1]
    assert event["action"] == "logout_session"
    assert event["status"] == "success"
    assert len(str(event["session_id_sha256"])) == 64
    assert "session-secret-1" not in json.dumps(event)


def test_logout_cross_account_attempt_fails_closed_and_preserves_session(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    store, central, lifecycle = _services(database)
    owner = central.sign_in(_identity("google-owner"))
    attacker = central.sign_in(_identity("google-attacker"))
    _persist_session(
        store,
        session_id="owner-session",
        user_id=owner.user_id,
        tenant_id=owner.tenant_id,
        credential_seed="owner-credential",
    )

    with pytest.raises(CentralIdentityError, match="another canonical account"):
        lifecycle.logout_session(
            authenticated_user_id=attacker.user_id,
            authenticated_tenant_id=attacker.tenant_id,
            session_id="owner-session",
        )

    persisted = store.get_session("owner-session")
    assert persisted is not None and persisted.revoked_at is None
    assert _events(database)[-1]["status"] == "denied"


def test_revoke_all_requires_recent_auth_and_is_account_scoped(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    store, central, lifecycle = _services(database)
    first = central.sign_in(_identity("google-first"))
    second = central.sign_in(_identity("google-second"))
    for session_id in ("first-1", "first-2"):
        _persist_session(
            store,
            session_id=session_id,
            user_id=first.user_id,
            tenant_id=first.tenant_id,
            credential_seed=session_id,
        )
    _persist_session(
        store,
        session_id="second-1",
        user_id=second.user_id,
        tenant_id=second.tenant_id,
        credential_seed="second-1",
    )

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        lifecycle.revoke_all_sessions(
            authenticated_user_id=first.user_id,
            authenticated_tenant_id=first.tenant_id,
            recent_authentication_verified=False,
        )

    assert store.get_session("first-1").revoked_at is None  # type: ignore[union-attr]
    assert lifecycle.revoke_all_sessions(
        authenticated_user_id=first.user_id,
        authenticated_tenant_id=first.tenant_id,
        recent_authentication_verified=True,
    ) == 2

    assert store.get_session("first-1").revoked_at is not None  # type: ignore[union-attr]
    assert store.get_session("first-2").revoked_at is not None  # type: ignore[union-attr]
    assert store.get_session("second-1").revoked_at is None  # type: ignore[union-attr]
    event = _events(database)[-1]
    assert event["action"] == "revoke_all_sessions"
    assert event["status"] == "success"
    assert event["revoked_count"] == 2


def test_revoke_all_is_idempotent_after_restart(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    store, central, lifecycle = _services(database)
    account = central.sign_in(_identity("google-1"))
    _persist_session(
        store,
        session_id="session-1",
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        credential_seed="credential-1",
    )

    assert lifecycle.revoke_all_sessions(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
    ) == 1

    restarted_store, _, restarted_lifecycle = _services(database)
    assert restarted_lifecycle.revoke_all_sessions(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
    ) == 0
    persisted = restarted_store.get_session("session-1")
    assert persisted is not None and persisted.revoked_at is not None
