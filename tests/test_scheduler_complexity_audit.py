"""Safety tests for the non-production scheduler complexity audit utility."""

from __future__ import annotations

import pytest

from tools.performance.scheduler_complexity_audit import characterize


def test_scheduler_complexity_audit_preserves_deterministic_selection() -> None:
    result = characterize(workers=4, seeded_leases=2)

    assert result.workers == 4
    assert result.seeded_leases == 2
    assert result.selected_worker == "worker-000002"
    assert result.active_count_calls == 0
    assert result.bulk_active_count_calls == 1
    assert result.lease_items_scanned == 2


def test_scheduler_complexity_audit_scans_each_active_lease_once() -> None:
    result = characterize(workers=1000, seeded_leases=1000)

    assert result.active_count_calls == 0
    assert result.bulk_active_count_calls == 1
    assert result.lease_items_scanned == result.seeded_leases


def test_scheduler_complexity_audit_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="workers"):
        characterize(workers=0, seeded_leases=0)
    with pytest.raises(ValueError, match="seeded_leases"):
        characterize(workers=2, seeded_leases=-1)
    with pytest.raises(ValueError, match="exceed workers"):
        characterize(workers=2, seeded_leases=3)
