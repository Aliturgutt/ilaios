"""Fail-closed admission of external perceptual Video QA evidence.

This module does not perform perception, call a model, or impersonate human
review. It admits review evidence that was produced outside the final evaluator
and binds it to one exact media artifact, reviewer identity, criteria digest,
and provenance record before converting it to the canonical ``VideoQaObservation``.

Deterministic TECHNICAL checks belong to the existing technical validation
pipeline. Deterministic visual/audio *signal* checks belong to
``media_signal_quality``. This contract is for semantic/perceptual VISUAL,
AUDIO, and BRAND review only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .video_quality import QaObservationSource, VideoQaObservation
from .video_skills import QaDomain


class PerceptualReviewError(ValueError):
    """Raised when external perceptual evidence cannot be admitted safely."""


class PerceptualReviewerKind(str, Enum):
    """Supported external reviewer origins."""

    HUMAN = "human"
    INDEPENDENT_MODEL = "independent_model"


_ALLOWED_DOMAINS = frozenset({QaDomain.VISUAL, QaDomain.AUDIO, QaDomain.BRAND})


@dataclass(frozen=True, slots=True)
class PerceptualReviewSubmission:
    """One immutable external review submission for one QA domain."""

    review_id: str
    domain: QaDomain
    artifact_sha256: str
    reviewer_id: str
    producer_id: str
    reviewer_kind: PerceptualReviewerKind
    criteria_id: str
    criteria_version: str
    criteria_sha256: str
    score: float
    threshold: float
    evidence_references: tuple[str, ...]
    provenance_reference: str
    repair_target: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "review_id",
            "reviewer_id",
            "producer_id",
            "criteria_id",
            "criteria_version",
            "provenance_reference",
        ):
            _require_text(name, getattr(self, name))
        _require_sha256("artifact_sha256", self.artifact_sha256)
        _require_sha256("criteria_sha256", self.criteria_sha256)
        if self.domain not in _ALLOWED_DOMAINS:
            raise PerceptualReviewError(
                "perceptual review is limited to visual, audio, and brand domains"
            )
        if self.reviewer_id == self.producer_id:
            raise PerceptualReviewError(
                "perceptual reviewer must be independent from artifact producer"
            )
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise PerceptualReviewError(
                "perceptual review score and threshold must be normalized"
            )
        if not self.evidence_references:
            raise PerceptualReviewError(
                "perceptual review requires at least one evidence reference"
            )
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise PerceptualReviewError(
                "perceptual review evidence references must be unique"
            )
        for reference in self.evidence_references:
            _require_text("evidence_reference", reference)
        if self.passed:
            if self.repair_target is not None:
                raise PerceptualReviewError(
                    "passed perceptual review must not request repair"
                )
        else:
            if self.repair_target is None:
                raise PerceptualReviewError(
                    "failed perceptual review requires a bounded repair target"
                )
            _require_text("repair_target", self.repair_target)

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold

    @property
    def observation_source(self) -> QaObservationSource:
        if self.reviewer_kind is PerceptualReviewerKind.HUMAN:
            return QaObservationSource.HUMAN_REVIEW
        return QaObservationSource.INDEPENDENT_MODEL

    def as_observation(self) -> VideoQaObservation:
        """Convert admitted evidence to the canonical independent QA contract."""

        evidence_material = ",".join(self.evidence_references)
        return VideoQaObservation(
            observation_id=f"perceptual:{self.review_id}",
            domain=self.domain,
            artifact_sha256=self.artifact_sha256,
            observer_id=self.reviewer_id,
            producer_id=self.producer_id,
            source=self.observation_source,
            score=self.score,
            threshold=self.threshold,
            evidence_reference=(
                f"review:{self.review_id}:evidence:{evidence_material}"
            ),
            provenance_reference=(
                f"{self.provenance_reference}|criteria:{self.criteria_id}@"
                f"{self.criteria_version}:{self.criteria_sha256}"
            ),
            repair_target=self.repair_target,
        )


def admit_perceptual_reviews(
    submissions: tuple[PerceptualReviewSubmission, ...],
    *,
    artifact_sha256: str,
    producer_id: str,
) -> tuple[VideoQaObservation, ...]:
    """Validate a bounded review set and return deterministic observations."""

    _require_sha256("artifact_sha256", artifact_sha256)
    _require_text("producer_id", producer_id)
    if not submissions:
        raise PerceptualReviewError("perceptual review set must not be empty")

    review_ids = [submission.review_id for submission in submissions]
    if len(review_ids) != len(set(review_ids)):
        raise PerceptualReviewError("perceptual review IDs must be unique")
    domains = [submission.domain for submission in submissions]
    if len(domains) != len(set(domains)):
        raise PerceptualReviewError(
            "perceptual review set may contain at most one review per domain"
        )

    observations: list[VideoQaObservation] = []
    for submission in submissions:
        if submission.artifact_sha256 != artifact_sha256:
            raise PerceptualReviewError(
                "perceptual review artifact identity does not match target"
            )
        if submission.producer_id != producer_id:
            raise PerceptualReviewError(
                "perceptual review producer identity does not match target producer"
            )
        observations.append(submission.as_observation())
    return tuple(sorted(observations, key=lambda item: item.domain.value))


def _require_sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise PerceptualReviewError(
            f"{name} must be a lowercase SHA-256 digest"
        )


def _require_text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise PerceptualReviewError(f"{name} must be non-blank and trimmed")
