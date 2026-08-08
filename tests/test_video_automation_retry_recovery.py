from __future__ import annotations

from src.video_automation.configuration import BudgetPolicy, RetryPolicy
from src.video_automation.retry_recovery import RetryRecoveryController


def test_retry_requires_retryable_failure_remaining_attempt_and_budget() -> None:
    decision = RetryRecoveryController().decide(
        attempt=1,
        retryable=True,
        estimated_retry_cost=1.0,
        retry_policy=RetryPolicy(max_attempts=3, initial_backoff_seconds=2.0, max_backoff_seconds=10.0),
        budget_policy=BudgetPolicy(max_retry_cost=2.0),
    )
    assert decision.retry is True
    assert decision.next_attempt == 2
    assert decision.backoff_seconds == 2.0


def test_retry_limit_is_enforced() -> None:
    decision = RetryRecoveryController().decide(
        attempt=2,
        retryable=True,
        estimated_retry_cost=0.0,
        retry_policy=RetryPolicy(max_attempts=2),
        budget_policy=BudgetPolicy(max_retry_cost=1.0),
    )
    assert decision.retry is False
    assert decision.reason == "retry limit reached"


def test_retry_cannot_bypass_budget() -> None:
    decision = RetryRecoveryController().decide(
        attempt=1,
        retryable=True,
        estimated_retry_cost=2.0,
        retry_policy=RetryPolicy(max_attempts=3),
        budget_policy=BudgetPolicy(max_retry_cost=1.0),
    )
    assert decision.retry is False
    assert decision.reason == "retry cost exceeds budget"
