from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.video_automation.provider_health import (
    CircuitState,
    ProviderHealthError,
    ProviderHealthStore,
)


def _now() -> datetime:
    return datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


def test_provider_circuit_opens_after_failure_threshold_and_survives_restart(
    tmp_path: Path,
) -> None:
    store = ProviderHealthStore(
        tmp_path, failure_threshold=2, cooldown=timedelta(minutes=5)
    )
    assert store.record_failure("provider-a", reason="timeout", now=_now()).state is CircuitState.CLOSED
    opened = store.record_failure(
        "provider-a", reason="upstream-5xx", now=_now() + timedelta(seconds=1)
    )
    assert opened.state is CircuitState.OPEN

    restarted = ProviderHealthStore(
        tmp_path, failure_threshold=2, cooldown=timedelta(minutes=5)
    )
    with pytest.raises(ProviderHealthError, match="canonical routing"):
        restarted.assert_candidate_eligible(
            "provider-a", now=_now() + timedelta(minutes=1)
        )


def test_open_circuit_becomes_half_open_after_cooldown() -> None:
    store = ProviderHealthStore(
        Path("/tmp") / "ilaios-provider-health-test-half-open",
        failure_threshold=1,
        cooldown=timedelta(minutes=5),
    )
    now = _now()
    store.record_failure("provider-half-open", reason="timeout", now=now)
    snapshot = store.snapshot(
        "provider-half-open", now=now + timedelta(minutes=6)
    )
    assert snapshot.state is CircuitState.HALF_OPEN


def test_half_open_failure_reopens_and_success_recovers(tmp_path: Path) -> None:
    store = ProviderHealthStore(
        tmp_path, failure_threshold=1, cooldown=timedelta(seconds=10)
    )
    now = _now()
    store.record_failure("provider-a", reason="timeout", now=now)
    assert store.snapshot("provider-a", now=now + timedelta(seconds=11)).state is CircuitState.HALF_OPEN
    assert store.record_failure(
        "provider-a", reason="probe failed", now=now + timedelta(seconds=12)
    ).state is CircuitState.OPEN
    recovered = store.record_success("provider-a", now=now + timedelta(seconds=13))
    assert recovered.state is CircuitState.CLOSED
    assert recovered.consecutive_failures == 0


def test_health_store_never_returns_a_fallback_provider(tmp_path: Path) -> None:
    store = ProviderHealthStore(tmp_path, failure_threshold=1)
    store.record_failure("provider-a", reason="timeout", now=_now())
    with pytest.raises(ProviderHealthError):
        store.assert_candidate_eligible("provider-a", now=_now())
    assert not hasattr(store, "select_provider")
    assert not hasattr(store, "fallback")
