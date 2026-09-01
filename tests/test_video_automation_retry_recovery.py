from __future__ import annotations

import pytest

from src.video_automation.configuration import BudgetPolicy, RetryPolicy
from src.video_automation.retry_recovery import (
    FailureKind,
    FailureObservation,
    RetryRecoveryController,
    RetryRecoveryError,
)


def test_retry_requires_retryable_failure_remaining_attempt_and_budget() -> None:
    decision = RetryRecoveryController().decide(
        attempt=1,
        retryable=True,
        estimated_retry_cost=1.0,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_backoff_seconds=2.0,
            max_backoff_seconds=10.0,
        ),
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


def test_m27_classifies_transient_failures_as_retryable() -> None:
    controller = RetryRecoveryController()
    retryable_kinds = (
        FailureKind.TIMEOUT,
        FailureKind.RATE_LIMITED,
        FailureKind.PROVIDER_UNAVAILABLE,
        FailureKind.NETWORK,
    )

    for kind in retryable_kinds:
        classification = controller.classify(
            FailureObservation(kind, "temporary failure")
        )
        assert classification.kind is kind
        assert classification.retryable is True


def test_m27_classifies_permanent_failures_as_non_retryable() -> None:
    controller = RetryRecoveryController()
    non_retryable_kinds = (
        FailureKind.VALIDATION,
        FailureKind.AUTHENTICATION,
        FailureKind.AUTHORIZATION,
        FailureKind.INVALID_REQUEST,
        FailureKind.POLICY,
        FailureKind.UNKNOWN,
    )

    for kind in non_retryable_kinds:
        classification = controller.classify(
            FailureObservation(kind, "permanent failure")
        )
        assert classification.kind is kind
        assert classification.retryable is False


def test_m27_decision_derives_retryability_from_failure_classification() -> None:
    decision = RetryRecoveryController().decide_failure(
        attempt=1,
        failure=FailureObservation(FailureKind.TIMEOUT, "provider timed out"),
        estimated_retry_cost=1.0,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_backoff_seconds=2.0,
            max_backoff_seconds=10.0,
        ),
        budget_policy=BudgetPolicy(max_retry_cost=2.0),
    )
    assert decision.retry is True
    assert decision.classification is not None
    assert decision.classification.kind is FailureKind.TIMEOUT
    assert decision.classification.retryable is True


def test_m27_non_retryable_failure_never_retries() -> None:
    decision = RetryRecoveryController().decide_failure(
        attempt=1,
        failure=FailureObservation(
            FailureKind.VALIDATION,
            "invalid generated artifact",
        ),
        estimated_retry_cost=0.0,
        retry_policy=RetryPolicy(max_attempts=3),
        budget_policy=BudgetPolicy(max_retry_cost=10.0),
    )
    assert decision.retry is False
    assert decision.next_attempt is None
    assert decision.classification is not None
    assert decision.classification.retryable is False


def test_m27_rejects_invalid_attempt_before_retry() -> None:
    with pytest.raises(RetryRecoveryError, match="attempt must be >= 1"):
        RetryRecoveryController().decide_failure(
            attempt=0,
            failure=FailureObservation(FailureKind.TIMEOUT),
            estimated_retry_cost=0.0,
            retry_policy=RetryPolicy(max_attempts=3),
            budget_policy=BudgetPolicy(max_retry_cost=10.0),
        )
