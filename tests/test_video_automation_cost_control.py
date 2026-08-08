from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.video_automation.configuration import BudgetPolicy
from src.video_automation.cost_control import CostControlError, CostController
from src.video_automation.models import CostRecord


def _record(estimated: float, actual: float | None) -> CostRecord:
    return CostRecord(
        job_id="job-1",
        provider="provider-a",
        operation="video.generate",
        estimated_cost=estimated,
        actual_cost=actual,
        currency="USD",
        timestamp=datetime.now(timezone.utc),
    )


def test_summary_tracks_estimated_and_actual_cost() -> None:
    summary = CostController().summarize((_record(1.0, 0.8), _record(2.0, None)))
    assert summary.estimated_total == 3.0
    assert summary.actual_total == 2.8


def test_video_budget_is_enforced() -> None:
    with pytest.raises(CostControlError, match="exceeds budget"):
        CostController().enforce_video_budget(
            (_record(3.0, 3.0),),
            BudgetPolicy(max_cost_per_video=2.0),
        )


def test_currency_mismatch_fails_closed() -> None:
    with pytest.raises(CostControlError, match="currency"):
        CostController().enforce_video_budget(
            (_record(1.0, 1.0),),
            BudgetPolicy(currency="EUR", max_cost_per_video=2.0),
        )
