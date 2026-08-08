"""Deterministic confidence scoring for ILAIOS."""

from dataclasses import dataclass
from typing import Literal

from src.core.validation_pipeline import ValidationResult

ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    """Immutable confidence assessment derived from validation output."""

    score: int
    level: ConfidenceLevel
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the confidence score boundary."""
        if not 0 <= self.score <= 100:
            raise ValueError(
                "Confidence score must be between 0 and 100"
            )


class ConfidenceScorer:
    """Convert validation results into deterministic confidence results."""

    ERROR_PENALTY: int = 20
    FAILED_WITHOUT_ERRORS_PENALTY: int = 50

    def score(
        self,
        validation_result: ValidationResult,
    ) -> ConfidenceResult:
        """Calculate confidence from one validation result."""
        if not isinstance(validation_result, ValidationResult):
            raise TypeError(
                "validation_result must be a ValidationResult"
            )

        score = 100
        reasons: list[str] = []

        for error in validation_result.errors:
            score -= self.ERROR_PENALTY
            reasons.append(f"validation_error: {error}")

        if (
            not validation_result.passed
            and not validation_result.errors
        ):
            score -= self.FAILED_WITHOUT_ERRORS_PENALTY
            reasons.append("validation_failed_without_errors")

        bounded_score = max(0, score)

        return ConfidenceResult(
            score=bounded_score,
            level=self._level_for_score(bounded_score),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _level_for_score(score: int) -> ConfidenceLevel:
        """Map a numeric score to its deterministic confidence level."""
        if score >= 90:
            return "high"

        if score >= 70:
            return "medium"

        return "low"
