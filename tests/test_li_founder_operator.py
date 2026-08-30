from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from services.control_plane.migrations import migrate_database
from services.identity import IdentityKind, Principal
from services.li_founder_operator import (
    LiAccessError,
    LiConfigurationError,
    LiFounderConfig,
    LiFounderOperator,
    LiMemoryError,
)

_NOW = datetime(2026, 8, 31, 0, 30, tzinfo=UTC)
_FOUNDER_USER = "usr_founder"
_FOUNDER_TENANT = "tnt_founder"


def _identity_database(path: Path) -> Path:
    migrate_database(path)
    timestamp = _NOW.isoformat()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants VALUES (?, 'ACTIVE', ?, ?)",
            (_FOUNDER_TENANT, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO identity_users VALUES (?, 1, ?, ?)",
            (_FOUNDER_USER, timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO identity_memberships
            (tenant_id, user_id, role, status, is_primary, created_at, updated_at)
            VALUES (?, ?, 'OWNER', 'ACTIVE', 1, ?, ?)
            """,
            (_FOUNDER_TENANT, _FOUNDER_USER, timestamp, timestamp),
        )
    return path


def _principal(
    *,
    user_id: str = _FOUNDER_USER,
    tenant_id: str = _FOUNDER_TENANT,
    role: str = "OWNER",
    kind: IdentityKind = IdentityKind.HUMAN,
) -> Principal:
    return Principal(
        principal_id=user_id,
        tenant_id=tenant_id,
        kind=kind,
        roles=frozenset({role}),
        attributes=frozenset(),
        authentication_methods=frozenset(),
    )


def _operator(tmp_path: Path) -> LiFounderOperator:
    identity = _identity_database(tmp_path / "identity.db")
    return LiFounderOperator(
        config=LiFounderConfig(
            user_id=_FOUNDER_USER,
            tenant_id=_FOUNDER_TENANT,
            database_path=tmp_path / "li.db",
        ),
        identity_database=identity,
        runtime_environment={"ILAIOS_RELEASE_SHA": "a" * 40},
    )


def test_li_configuration_is_optional_but_partial_configuration_fails_closed(
    tmp_path: Path,
) -> None:
    assert LiFounderConfig.from_environment({}) is None
    with pytest.raises(LiConfigurationError):
        LiFounderConfig.from_environment(
            {
                "ILAIOS_LI_FOUNDER_USER_ID": _FOUNDER_USER,
                "ILAIOS_LI_DATABASE_PATH": str(tmp_path / "li.db"),
            }
        )




def test_li_memory_database_must_not_share_canonical_identity_file(
    tmp_path: Path,
) -> None:
    identity = _identity_database(tmp_path / "identity.db")
    with pytest.raises(LiConfigurationError):
        LiFounderOperator(
            config=LiFounderConfig(
                user_id=_FOUNDER_USER,
                tenant_id=_FOUNDER_TENANT,
                database_path=identity,
            ),
            identity_database=identity,
        )

def test_only_exact_canonical_founder_owner_can_access_li(tmp_path: Path) -> None:
    operator = _operator(tmp_path)
    operator.authorize(_principal())

    for denied in (
        _principal(user_id="usr_customer"),
        _principal(tenant_id="tnt_customer"),
        _principal(role="MEMBER"),
        _principal(kind=IdentityKind.SERVICE),
    ):
        with pytest.raises(LiAccessError):
            operator.authorize(denied)


def test_li_memory_persists_across_operator_instances(tmp_path: Path) -> None:
    identity = _identity_database(tmp_path / "identity.db")
    config = LiFounderConfig(
        user_id=_FOUNDER_USER,
        tenant_id=_FOUNDER_TENANT,
        database_path=tmp_path / "li.db",
    )
    first = LiFounderOperator(config=config, identity_database=identity)
    stored = first.remember(
        _principal(),
        kind="semantic",
        content="ILAIOS canonical Core must remain in place.",
        now=_NOW,
    )

    second = LiFounderOperator(config=config, identity_database=identity)
    memories = second.list_memories(_principal())

    assert len(memories) == 1
    assert memories[0] == stored
    assert memories[0].owner_user_id == _FOUNDER_USER
    assert memories[0].owner_tenant_id == _FOUNDER_TENANT


def test_customer_owner_cannot_read_founder_memory(tmp_path: Path) -> None:
    operator = _operator(tmp_path)
    operator.remember(
        _principal(),
        kind="episodic",
        content="Founder-only memory.",
        now=_NOW,
    )
    with pytest.raises(LiAccessError):
        operator.list_memories(
            _principal(user_id="usr_customer", tenant_id=_FOUNDER_TENANT)
        )


def test_secret_like_memory_is_rejected_before_persistence(tmp_path: Path) -> None:
    operator = _operator(tmp_path)
    with pytest.raises(LiMemoryError):
        operator.remember(
            _principal(),
            kind="working",
            content="api_key=do-not-store-this",
            now=_NOW,
        )
    assert operator.list_memories(_principal()) == ()


def test_snapshot_reads_live_canonical_membership_and_release_state(
    tmp_path: Path,
) -> None:
    operator = _operator(tmp_path)
    operator.remember(
        _principal(),
        kind="working",
        content="Phase 1 current task.",
        now=_NOW,
    )

    snapshot = operator.snapshot(_principal(), now=_NOW)

    assert snapshot["name"] == "Li"
    assert snapshot["founder_operator"] is True
    assert snapshot["memory_count"] == 1
    system = snapshot["system"]
    assert isinstance(system, dict)
    assert system["scope"] == "app_runtime_identity"
    assert system["service"] == "app.ilaios.com"
    assert system["tenant_status"] == "ACTIVE"
    assert system["membership_status"] == "ACTIVE"
    assert system["release_sha"] == "a" * 40


def test_snapshot_fails_closed_when_canonical_membership_is_suspended(
    tmp_path: Path,
) -> None:
    operator = _operator(tmp_path)
    with sqlite3.connect(operator.identity_database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status = 'SUSPENDED' "
            "WHERE tenant_id = ? AND user_id = ?",
            (_FOUNDER_TENANT, _FOUNDER_USER),
        )

    with pytest.raises(LiAccessError):
        operator.snapshot(_principal(), now=_NOW)
