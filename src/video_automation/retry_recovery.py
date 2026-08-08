"""Canonical M27 bounded deterministic retry and failure recovery."""

from __future__ import annotations

from dataclasses import dataclass

from .configuration import BudgetPolicy, RetryPolicy


class RetryRecoveryError(ValueError):
    """Raised when retry inputs are invalid."""


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    next_attempt: int | None
    backoff_seconds: float | None
    reason: str


class RetryRecoveryController:
    """Classify retryability while enforcing retry and cost bounds."""

    def decide(
        self,
        *,
        attempt: int,
        retryable: bool,
        estimated_retry_cost: float,
        retry_policy: RetryPolicy,
        budget_policy: BudgetPolicy,
    ) -> RetryDecision:
        if attempt < 1:
            raise RetryRecoveryError("attempt must be >= 1")
        if estimated_retry_cost < 0:
            raise RetryRecoveryError("estimated_retry_cost must be >= 0")
        if not retryable:
            return RetryDecision(False, None, None, "failure is non-retryable")
        if attempt >= retry_policy.max_attempts:
            return RetryDecision(False, None, None, "retry limit reached")
        if estimated_retry_cost > budget_policy.max_retry_cost:
            return RetryDecision(False, None, None, "retry cost exceeds budget")

        backoff = retry_policy.initial_backoff_seconds * (2 ** (attempt - 1))
        bounded_backoff = min(backoff, retry_policy.max_backoff_seconds)
        return RetryDecision(True, attempt + 1, bounded_backoff, "retry permitted")
