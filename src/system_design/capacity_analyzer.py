"""Deterministic capacity estimation for the ILAIOS system-design skill.

The estimates in this module are planning inputs, not scalability proof. Production
claims require measured load-test and runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

_SECONDS_PER_DAY = 86_400
_SECONDS_PER_30_DAY_MONTH = 2_592_000
_SECONDS_PER_YEAR = 31_536_000


class CapacityInputError(ValueError):
    """Raised when a capacity request is internally invalid."""


@dataclass(frozen=True, slots=True)
class CapacityInput:
    """Explicit demand assumptions used by deterministic capacity estimation."""

    concurrent_users: int | None = None
    requests_per_second: float | None = None
    requests_per_user_per_second: float | None = None
    peak_factor: float = 1.5
    avg_request_bytes: int = 1_024
    avg_response_bytes: int = 8_192
    read_ratio: float = 0.8
    write_ratio: float = 0.2
    avg_write_bytes: int = 2_048
    sustainable_rps_per_instance: float | None = None
    target_utilization: float = 0.65
    availability_slo: float = 0.999
    monthly_budget: float | None = None
    estimated_monthly_cost: float | None = None


@dataclass(frozen=True, slots=True)
class CapacityIssue:
    """A structured uncertainty or validation issue."""

    code: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class CapacityEstimate:
    """Derived planning figures with explicit assumptions and uncertainty."""

    base_rps: float | None
    peak_rps: float | None
    read_rps: float | None
    write_rps: float | None
    ingress_bits_per_second: float | None
    egress_bits_per_second: float | None
    write_storage_bytes_per_day: float | None
    minimum_instances: int | None
    downtime_seconds_per_30_day_month: float
    downtime_seconds_per_year: float
    budget_headroom: float | None
    assumptions: tuple[str, ...]
    issues: tuple[CapacityIssue, ...]

    @property
    def is_actionable(self) -> bool:
        """Return whether enough demand information exists for sizing decisions."""

        return self.peak_rps is not None and not any(
            issue.severity == "error" for issue in self.issues
        )


def _validate_non_negative(name: str, value: float | int | None) -> None:
    if value is not None and value < 0:
        raise CapacityInputError(f"{name} must be non-negative")


def _validate_input(data: CapacityInput) -> None:
    _validate_non_negative("concurrent_users", data.concurrent_users)
    _validate_non_negative("requests_per_second", data.requests_per_second)
    _validate_non_negative(
        "requests_per_user_per_second", data.requests_per_user_per_second
    )
    _validate_non_negative("avg_request_bytes", data.avg_request_bytes)
    _validate_non_negative("avg_response_bytes", data.avg_response_bytes)
    _validate_non_negative("avg_write_bytes", data.avg_write_bytes)
    _validate_non_negative(
        "sustainable_rps_per_instance", data.sustainable_rps_per_instance
    )
    _validate_non_negative("monthly_budget", data.monthly_budget)
    _validate_non_negative("estimated_monthly_cost", data.estimated_monthly_cost)

    if data.peak_factor < 1:
        raise CapacityInputError("peak_factor must be at least 1")
    if not 0 < data.target_utilization <= 1:
        raise CapacityInputError("target_utilization must be in (0, 1]")
    if not 0 < data.availability_slo <= 1:
        raise CapacityInputError("availability_slo must be in (0, 1]")
    if not 0 <= data.read_ratio <= 1 or not 0 <= data.write_ratio <= 1:
        raise CapacityInputError("read_ratio and write_ratio must be in [0, 1]")
    if abs((data.read_ratio + data.write_ratio) - 1.0) > 1e-9:
        raise CapacityInputError("read_ratio and write_ratio must sum to 1")


def analyze_capacity(data: CapacityInput) -> CapacityEstimate:
    """Estimate demand without pretending that a user count proves throughput.

    Explicit RPS has precedence. Otherwise concurrent users must be paired with a
    request-rate assumption. A bare value such as "one million users" remains
    ambiguous and deliberately produces no throughput sizing result.
    """

    _validate_input(data)
    assumptions: list[str] = []
    issues: list[CapacityIssue] = []

    base_rps: float | None
    if data.requests_per_second is not None:
        base_rps = data.requests_per_second
        assumptions.append("explicit_requests_per_second_used")
        if (
            data.concurrent_users is not None
            and data.requests_per_user_per_second is not None
        ):
            issues.append(
                CapacityIssue(
                    "DEMAND_INPUT_OVERRIDE",
                    "info",
                    "Explicit requests_per_second overrides the derived user-rate "
                    "value.",
                )
            )
    elif (
        data.concurrent_users is not None
        and data.requests_per_user_per_second is not None
    ):
        base_rps = data.concurrent_users * data.requests_per_user_per_second
        assumptions.append("rps_derived_from_concurrency_and_per_user_rate")
    else:
        base_rps = None
        issues.append(
            CapacityIssue(
                "AMBIGUOUS_DEMAND",
                "warning",
                "User count alone cannot determine throughput; provide explicit RPS or "
                "concurrent_users plus requests_per_user_per_second.",
            )
        )

    peak_rps = base_rps * data.peak_factor if base_rps is not None else None
    read_rps = peak_rps * data.read_ratio if peak_rps is not None else None
    write_rps = peak_rps * data.write_ratio if peak_rps is not None else None
    ingress = (
        peak_rps * data.avg_request_bytes * 8 if peak_rps is not None else None
    )
    egress = (
        peak_rps * data.avg_response_bytes * 8 if peak_rps is not None else None
    )

    average_write_rps = (
        base_rps * data.write_ratio if base_rps is not None else None
    )
    write_storage = (
        average_write_rps * data.avg_write_bytes * _SECONDS_PER_DAY
        if average_write_rps is not None
        else None
    )

    minimum_instances: int | None = None
    if peak_rps is not None and data.sustainable_rps_per_instance is not None:
        if data.sustainable_rps_per_instance == 0:
            issues.append(
                CapacityIssue(
                    "ZERO_INSTANCE_CAPACITY",
                    "error",
                    "sustainable_rps_per_instance must be greater than zero when used.",
                )
            )
        else:
            effective_rps = (
                data.sustainable_rps_per_instance * data.target_utilization
            )
            minimum_instances = max(1, ceil(peak_rps / effective_rps))
            assumptions.append("instance_count_uses_sustainable_measured_rps")
    elif peak_rps is not None:
        issues.append(
            CapacityIssue(
                "INSTANCE_BENCHMARK_MISSING",
                "warning",
                "Instance count cannot be sized until sustainable per-instance RPS is "
                "measured or supplied.",
            )
        )

    monthly_downtime = _SECONDS_PER_30_DAY_MONTH * (1 - data.availability_slo)
    yearly_downtime = _SECONDS_PER_YEAR * (1 - data.availability_slo)

    budget_headroom: float | None = None
    if data.monthly_budget is not None:
        if data.estimated_monthly_cost is None:
            issues.append(
                CapacityIssue(
                    "COST_EVIDENCE_MISSING",
                    "warning",
                    "A monthly budget exists, but measured or quoted monthly cost is "
                    "missing; the budget gate is unresolved.",
                )
            )
        else:
            budget_headroom = data.monthly_budget - data.estimated_monthly_cost
            if budget_headroom < 0:
                issues.append(
                    CapacityIssue(
                        "BUDGET_EXCEEDED",
                        "error",
                        "Estimated monthly cost exceeds the supplied budget envelope.",
                    )
                )

    assumptions.append("peak_rps_equals_base_rps_times_peak_factor")
    assumptions.append("storage_uses_average_rps_not_peak_rps")
    assumptions.append("capacity_estimate_requires_load_test_for_verification")

    return CapacityEstimate(
        base_rps=base_rps,
        peak_rps=peak_rps,
        read_rps=read_rps,
        write_rps=write_rps,
        ingress_bits_per_second=ingress,
        egress_bits_per_second=egress,
        write_storage_bytes_per_day=write_storage,
        minimum_instances=minimum_instances,
        downtime_seconds_per_30_day_month=monthly_downtime,
        downtime_seconds_per_year=yearly_downtime,
        budget_headroom=budget_headroom,
        assumptions=tuple(assumptions),
        issues=tuple(issues),
    )
