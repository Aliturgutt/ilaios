"""Canonical M27 bounded deterministic retry and failure recovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .configuration import BudgetPolicy, RetryPolicy


class RetryRecoveryError(ValueError):
    """Raised when retry inputs are invalid."""


class FailureKind(str, Enum):
    """Canonical failure classes used to determine retryability."""

    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INVALID_REQUEST = "invalid_request"
    POLICY = "policy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FailureObservation:
    """Normalized failure input presented to the recovery controller."""

    kind: FailureKind
    message: str = ""


@dataclass(frozen=True, slots=True)
class FailureClassification:
    """Deterministic classification result used by retry policy."""

    kind: FailureKind
    retryable: bool
    reason: str


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    next_attempt: int | None
    backoff_seconds: float | None
    reason: str
    classification: FailureClassification | None = None


class RetryRecoveryController:
    """Classify failures while enforcing deterministic retry and cost bounds."""

    _RETRYABLE_FAILURES = frozenset(
        {
            FailureKind.TIMEOUT,
            FailureKind.RATE_LIMITED,
            FailureKind.PROVIDER_UNAVAILABLE,
            FailureKind.NETWORK,
        }
    )

    def classify(self, failure: FailureObservation) -> FailureClassification:
        """Classify a normalized failure without caller-supplied retryability."""

        retryable = failure.kind in self._RETRYABLE_FAILURES
        reason = (
            f"{failure.kind.value} failure is retryable"
            if retryable
            else f"{failure.kind.value} failure is non-retryable"
        )
        return FailureClassification(failure.kind, retryable, reason)

    def decide_failure(
        self,
        *,
        attempt: int,
        failure: FailureObservation,
        estimated_retry_cost: float,
        retry_policy: RetryPolicy,
        budget_policy: BudgetPolicy,
    ) -> RetryDecision:
        """Classify a failure and then apply retry-count/backoff/budget bounds."""

        classification = self.classify(failure)
        decision = self._decide(
            attempt=attempt,
            retryable=classification.retryable,
            estimated_retry_cost=estimated_retry_cost,
            retry_policy=retry_policy,
            budget_policy=budget_policy,
        )
        return RetryDecision(
            decision.retry,
            decision.next_attempt,
            decision.backoff_seconds,
            decision.reason,
            classification,
        )

    def decide(
        self,
        *,
        attempt: int,
        retryable: bool,
        estimated_retry_cost: float,
        retry_policy: RetryPolicy,
        budget_policy: BudgetPolicy,
    ) -> RetryDecision:
        """Compatibility entry point for already-classified upstream failures."""

        return self._decide(
            attempt=attempt,
            retryable=retryable,
            estimated_retry_cost=estimated_retry_cost,
            retry_policy=retry_policy,
            budget_policy=budget_policy,
        )

    def _decide(
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
