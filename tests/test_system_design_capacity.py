"""Tests for deterministic system-design capacity estimation."""

from __future__ import annotations

import math

import pytest

from src.system_design.capacity_analyzer import (
    CapacityInput,
    CapacityInputError,
    analyze_capacity,
)


def test_bare_one_million_users_is_deliberately_ambiguous() -> None:
    estimate = analyze_capacity(CapacityInput(concurrent_users=1_000_000))
    assert estimate.base_rps is None
    assert estimate.peak_rps is None
    assert "AMBIGUOUS_DEMAND" in {issue.code for issue in estimate.issues}
    assert not estimate.is_actionable


def test_concurrency_and_request_rate_derive_peak_rps() -> None:
    estimate = analyze_capacity(
        CapacityInput(
            concurrent_users=10_000,
            requests_per_user_per_second=0.2,
            peak_factor=2.0,
        )
    )
    assert estimate.base_rps == 2_000
    assert estimate.peak_rps == 4_000
    assert estimate.read_rps == 3_200
    assert estimate.write_rps == 800


def test_explicit_rps_overrides_user_derived_rate() -> None:
    estimate = analyze_capacity(
        CapacityInput(
            concurrent_users=1_000,
            requests_per_user_per_second=10,
            requests_per_second=250,
            peak_factor=2,
        )
    )
    assert estimate.base_rps == 250
    assert estimate.peak_rps == 500
    assert "DEMAND_INPUT_OVERRIDE" in {issue.code for issue in estimate.issues}


def test_instance_sizing_reserves_target_utilization_headroom() -> None:
    estimate = analyze_capacity(
        CapacityInput(
            requests_per_second=1_000,
            peak_factor=1,
            sustainable_rps_per_instance=400,
            target_utilization=0.5,
        )
    )
    assert estimate.minimum_instances == 5


def test_write_storage_uses_average_not_peak_rps() -> None:
    estimate = analyze_capacity(
        CapacityInput(
            requests_per_second=100,
            peak_factor=3,
            read_ratio=0.5,
            write_ratio=0.5,
            avg_write_bytes=100,
        )
    )
    assert estimate.write_storage_bytes_per_day == 50 * 100 * 86_400


def test_availability_budget_is_calculated_from_slo() -> None:
    estimate = analyze_capacity(
        CapacityInput(requests_per_second=1, availability_slo=0.9999)
    )
    assert math.isclose(estimate.downtime_seconds_per_30_day_month, 259.2)
    assert math.isclose(estimate.downtime_seconds_per_year, 3_153.6)


def test_budget_gate_fails_when_cost_exceeds_envelope() -> None:
    estimate = analyze_capacity(
        CapacityInput(
            requests_per_second=100,
            monthly_budget=1_000,
            estimated_monthly_cost=1_200,
        )
    )
    assert estimate.budget_headroom == -200
    assert "BUDGET_EXCEEDED" in {issue.code for issue in estimate.issues}
    assert not estimate.is_actionable


def test_invalid_ratios_are_rejected() -> None:
    with pytest.raises(CapacityInputError, match="must sum to 1"):
        analyze_capacity(
            CapacityInput(requests_per_second=1, read_ratio=0.7, write_ratio=0.4)
        )
