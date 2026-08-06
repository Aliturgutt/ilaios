"""Tests for deterministic confidence scoring."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from src.core.confidence_scoring import (
    ConfidenceResult,
    ConfidenceScorer,
)
from src.core.validation_pipeline import ValidationResult


def test_successful_validation_has_full_confidence() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=True,
        errors=(),
    )

    result = scorer.score(validation_result)

    assert result == ConfidenceResult(
        score=100,
        level="high",
        reasons=(),
    )


def test_single_error_produces_medium_confidence() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=("one error",),
    )

    result = scorer.score(validation_result)

    assert result == ConfidenceResult(
        score=80,
        level="medium",
        reasons=("validation_error: one error",),
    )


def test_two_errors_produce_low_confidence() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=("first error", "second error"),
    )

    result = scorer.score(validation_result)

    assert result == ConfidenceResult(
        score=60,
        level="low",
        reasons=(
            "validation_error: first error",
            "validation_error: second error",
        ),
    )


def test_failure_without_errors_uses_fixed_penalty() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=(),
    )

    result = scorer.score(validation_result)

    assert result == ConfidenceResult(
        score=50,
        level="low",
        reasons=("validation_failed_without_errors",),
    )


def test_three_errors_produce_score_of_forty() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=("error-1", "error-2", "error-3"),
    )

    result = scorer.score(validation_result)

    assert result.score == 40
    assert result.level == "low"
    assert len(result.reasons) == 3


def test_four_errors_produce_score_of_twenty() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=("error-1", "error-2", "error-3", "error-4"),
    )

    result = scorer.score(validation_result)

    assert result.score == 20
    assert result.level == "low"
    assert len(result.reasons) == 4


def test_five_errors_produce_minimum_score() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=(
            "error-1",
            "error-2",
            "error-3",
            "error-4",
            "error-5",
        ),
    )

    result = scorer.score(validation_result)

    assert result.score == 0
    assert result.level == "low"
    assert len(result.reasons) == 5


def test_score_never_drops_below_zero() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=(
            "error-1",
            "error-2",
            "error-3",
            "error-4",
            "error-5",
            "error-6",
        ),
    )

    result = scorer.score(validation_result)

    assert result.score == 0
    assert result.level == "low"
    assert len(result.reasons) == 6


def test_same_input_produces_same_result() -> None:
    scorer = ConfidenceScorer()
    validation_result = ValidationResult(
        passed=False,
        errors=("deterministic failure",),
    )

    first_result = scorer.score(validation_result)
    second_result = scorer.score(validation_result)

    assert first_result == second_result


def test_confidence_result_is_immutable() -> None:
    result = ConfidenceResult(
        score=100,
        level="high",
        reasons=(),
    )

    with pytest.raises(FrozenInstanceError):
        setattr(result, "score", 0)  # noqa: B010


def test_negative_score_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Confidence score must be between 0 and 100",
    ):
        ConfidenceResult(
            score=-1,
            level="low",
            reasons=(),
        )


def test_score_above_one_hundred_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Confidence score must be between 0 and 100",
    ):
        ConfidenceResult(
            score=101,
            level="high",
            reasons=(),
        )


def test_invalid_input_type_is_rejected() -> None:
    scorer = ConfidenceScorer()
    invalid_result = cast(ValidationResult, object())

    with pytest.raises(
        TypeError,
        match="validation_result must be a ValidationResult",
    ):
        scorer.score(invalid_result)
