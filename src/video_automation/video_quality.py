"""Artifact-bound Video Factory quality evaluation primitives.

The foundation consumes externally produced observations for the canonical
visual, audio, brand, and technical QA domains.  It does not inspect media,
call providers, grant authority, publish, or self-generate evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from .video_skills import (
    FinalVideoEvaluation,
    IndependentVideoEvaluator,
    QaDomain,
    QaFinding,
    RepairRequest,
    SelectiveRepairController,
    VideoSkillError,
)


class VideoQualityError(VideoSkillError):
    """Raised when independent Video QA evidence cannot be accepted safely."""


class QaObservationSource(str, Enum):
    """Permitted origins for externally produced QA observations."""

    DETERMINISTIC_PROBE = "deterministic_probe"
    INDEPENDENT_MODEL = "independent_model"
    HUMAN_REVIEW = "human_review"


class VideoQaStatus(str, Enum):
    """Normalized disposition of one complete four-domain QA run."""

    ACCEPTED = "accepted"
    REPAIR_REQUIRED = "repair_required"


@dataclass(frozen=True, slots=True)
class VideoQaObservation:
    """One artifact-bound observation produced outside the final evaluator."""

    observation_id: str
    domain: QaDomain
    artifact_sha256: str
    observer_id: str
    producer_id: str
    source: QaObservationSource
    score: float
    threshold: float
    evidence_reference: str
    provenance_reference: str
    repair_target: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "observer_id",
            "producer_id",
            "evidence_reference",
            "provenance_reference",
        ):
            _require_text(name, getattr(self, name))
        _require_sha256(self.artifact_sha256)
        if self.observer_id == self.producer_id:
            raise VideoQualityError("QA observer must be independent from artifact producer")
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise VideoQualityError("QA observation score and threshold must be normalized")
        if not self.passed:
            if self.repair_target is None:
                raise VideoQualityError("failed QA observation requires a repair target")
            _require_text("repair_target", self.repair_target)
        elif self.repair_target is not None:
            raise VideoQualityError("passed QA observation must not request repair")

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold

    def as_finding(self) -> QaFinding:
        return QaFinding(
            finding_id=f"finding:{self.observation_id}",
            domain=self.domain,
            passed=self.passed,
            score=self.score,
            threshold=self.threshold,
            evidence_reference=self.evidence_reference,
            repair_target=self.repair_target,
        )


@dataclass(frozen=True, slots=True)
class VideoQaRun:
    """Immutable result of one complete independent QA aggregation."""

    run_id: str
    artifact_sha256: str
    status: VideoQaStatus
    observations: tuple[VideoQaObservation, ...]
    evaluation: FinalVideoEvaluation
    repairs: tuple[RepairRequest, ...]


class VideoQualityFoundation:
    """Fail-closed four-domain QA aggregation and bounded repair planning."""

    def __init__(self, *, max_repair_attempts: int = 2) -> None:
        self._evaluator = IndependentVideoEvaluator()
        self._repair = SelectiveRepairController(max_attempts=max_repair_attempts)

    def evaluate(
        self,
        artifact_sha256: str,
        observations: Sequence[VideoQaObservation],
        *,
        evaluator_id: str,
        prior_attempts: Mapping[str, int] | None = None,
    ) -> VideoQaRun:
        _require_sha256(artifact_sha256)
        _require_text("evaluator_id", evaluator_id)
        items = tuple(sorted(observations, key=lambda item: item.domain.value))
        _validate_observations(artifact_sha256, items, evaluator_id=evaluator_id)

        findings = tuple(item.as_finding() for item in items)
        attempts = {} if prior_attempts is None else dict(prior_attempts)
        known_findings = {finding.finding_id for finding in findings}
        unknown_attempts = set(attempts) - known_findings
        if unknown_attempts:
            raise VideoQualityError(
                "repair history references unknown findings: "
                + ", ".join(sorted(unknown_attempts))
            )

        evaluation = self._evaluator.evaluate(
            artifact_sha256,
            findings,
            evaluator_id=evaluator_id,
        )
        repairs = () if evaluation.passed else self._repair.plan(evaluation, attempts)
        status = (
            VideoQaStatus.ACCEPTED
            if evaluation.passed
            else VideoQaStatus.REPAIR_REQUIRED
        )
        run_id = _run_id(artifact_sha256, evaluator_id, items, repairs)
        return VideoQaRun(
            run_id=run_id,
            artifact_sha256=artifact_sha256,
            status=status,
            observations=items,
            evaluation=evaluation,
            repairs=repairs,
        )


def _validate_observations(
    artifact_sha256: str,
    observations: tuple[VideoQaObservation, ...],
    *,
    evaluator_id: str,
) -> None:
    domains = {item.domain for item in observations}
    if len(observations) != len(QaDomain) or domains != set(QaDomain):
        raise VideoQualityError(
            "Video QA requires exactly one visual, audio, brand, and technical observation"
        )
    ids = [item.observation_id for item in observations]
    if len(ids) != len(set(ids)):
        raise VideoQualityError("QA observation IDs must be unique")
    for item in observations:
        if item.artifact_sha256 != artifact_sha256:
            raise VideoQualityError("QA observation artifact identity does not match target")
    producer_ids = {item.producer_id for item in observations}
    observer_ids = {item.observer_id for item in observations}
    if evaluator_id in producer_ids:
        raise VideoQualityError("final evaluator cannot certify its own produced artifact")
    if evaluator_id in observer_ids:
        raise VideoQualityError("final evaluator must aggregate externally produced observations")


def _run_id(
    artifact_sha256: str,
    evaluator_id: str,
    observations: tuple[VideoQaObservation, ...],
    repairs: tuple[RepairRequest, ...],
) -> str:
    material = [f"artifact={artifact_sha256}", f"evaluator={evaluator_id}"]
    material.extend(
        "|".join(
            (
                item.observation_id,
                item.domain.value,
                item.observer_id,
                item.producer_id,
                item.source.value,
                format(item.score, ".12g"),
                format(item.threshold, ".12g"),
                item.evidence_reference,
                item.provenance_reference,
                item.repair_target or "",
            )
        )
        for item in observations
    )
    material.extend(
        f"repair={item.finding_id}|target={item.target}|attempt={item.attempt}"
        for item in repairs
    )
    digest = sha256("\n".join(material).encode()).hexdigest()
    return f"video-qa-{digest[:20]}"


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise VideoQualityError("artifact identity must be lowercase SHA-256")


def _require_text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise VideoQualityError(f"{name} must be non-blank and trimmed")
