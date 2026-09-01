"""Execution grant and kill-switch tests for PLATFORM.P11."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.runtime import (
    BlastRadiusBudget,
    ExecutionGrant,
    GrantError,
    GrantPolicy,
)


def _grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "grant-1",
        "worker-1",
        frozenset({"write"}),
        frozenset({"asset-a", "asset-b"}),
        now + timedelta(minutes=5),
        BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def test_scoped_grant_and_blast_radius_fail_closed() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    grant = _grant(now)
    policy = GrantPolicy()
    policy.authorize(
        grant, subject_id="worker-1", action="write", resource="asset-a", now=now
    )
    policy.record_side_effect(grant, "asset-a")

    with pytest.raises(GrantError, match="budget exhausted"):
        policy.authorize(
            grant,
            subject_id="worker-1",
            action="write",
            resource="asset-b",
            now=now,
        )


def test_revocation_blocks_an_otherwise_valid_grant() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    grant = _grant(now)
    policy = GrantPolicy()
    policy.revoke(grant.grant_id)
    with pytest.raises(GrantError, match="revoked"):
        policy.authorize(
            grant, subject_id="worker-1", action="write", resource="asset-a", now=now
        )


def test_killed_work_cannot_auto_resume() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    grant = _grant(now)
    policy = GrantPolicy()
    policy.kill("worker-1")

    with pytest.raises(GrantError, match="stopped"):
        policy.authorize(
            grant, subject_id="worker-1", action="write", resource="asset-a", now=now
        )
    with pytest.raises(GrantError, match="human approval"):
        policy.reset_stopped_subject("worker-1", human_approved=False)
