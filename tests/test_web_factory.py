"""Golden Web Factory workflow tests for PLATFORM.P17."""

from datetime import datetime, timedelta, timezone

import pytest

from services.integrations import GovernedWebFactory
from services.runtime import BlastRadiusBudget, ExecutionGrant, GrantPolicy


def _grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "web-grant", "web-worker", frozenset({"web.build"}),
        frozenset({"ilaios-official"}), now + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_golden_official_site_has_machine_readable_acceptance() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = GovernedWebFactory(GrantPolicy()).build_official_site(
        "ilaios-official", ("home", "product", "security", "contact"),
        grant=_grant(now), now=now,
    )
    assert result.accepted is True
    assert result.official_brand == "ILAIOS"
    assert len(result.artifact_hash) == 64


def test_golden_workflow_rejects_incomplete_site() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="canonical page set"):
        GovernedWebFactory(GrantPolicy()).build_official_site(
            "ilaios-official", ("home",), grant=_grant(now), now=now
        )
