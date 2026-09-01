"""Canonical M28 cost tracking and budget enforcement."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .configuration import BudgetPolicy
from .models import CostRecord


class CostControlError(ValueError):
    """Raised when a cost operation violates policy or currency consistency."""


@dataclass(frozen=True, slots=True)
class CostSummary:
    currency: str
    estimated_total: float
    actual_total: float


class CostController:
    """Aggregate provider costs and enforce deterministic video/retry limits."""

    def summarize(self, records: Iterable[CostRecord]) -> CostSummary:
        items = tuple(records)
        if not items:
            return CostSummary("USD", 0.0, 0.0)
        currencies = {record.currency for record in items}
        if len(currencies) != 1:
            raise CostControlError("cost records must use one currency")
        currency = next(iter(currencies))
        return CostSummary(
            currency=currency,
            estimated_total=sum(record.estimated_cost for record in items),
            actual_total=sum(
                record.estimated_cost if record.actual_cost is None else record.actual_cost
                for record in items
            ),
        )

    def enforce_video_budget(
        self,
        records: Iterable[CostRecord],
        policy: BudgetPolicy,
    ) -> CostSummary:
        summary = self.summarize(records)
        if summary.currency != policy.currency:
            raise CostControlError("cost currency does not match budget policy")
        if summary.estimated_total > policy.max_cost_per_video:
            raise CostControlError("estimated video cost exceeds budget")
        if summary.actual_total > policy.max_cost_per_video:
            raise CostControlError("actual video cost exceeds budget")
        return summary
