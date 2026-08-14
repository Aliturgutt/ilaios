"""Media quality deltas that extend, not replace, canonical Video acceptance.

Existing technical/signal/perceptual/four-domain QA and final acceptance remain the
authorities. This module contributes exact-artifact continuity evidence and a
bounded repair plan for failed targets only.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .final_episode_acceptance import FinalEpisodeQualityCheck


class MediaQualityControlError(ValueError):
    """Raised when quality/repair evidence cannot be admitted safely."""


@dataclass(frozen=True, slots=True)
class ContinuityQualityEvidence:
    artifact_sha256: str
    score: float
    threshold: float
    evaluator_id: str
    evidence_ref: str
    failed_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _sha256("artifact_sha256", self.artifact_sha256)
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise MediaQualityControlError("continuity score/threshold must be within [0, 1]")
        _text("evaluator_id", self.evaluator_id)
        _text("evidence_ref", self.evidence_ref)
        for target in self.failed_targets:
            _text("failed target", target)
        if self.passed and self.failed_targets:
            raise MediaQualityControlError(
                "passing continuity evidence cannot contain failed targets"
            )
        if not self.passed and not self.failed_targets:
            raise MediaQualityControlError(
                "failed continuity evidence requires bounded repair targets"
            )

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True, slots=True)
class RepairTarget:
    target: str
    prior_attempts: int
    max_attempts: int

    def __post_init__(self) -> None:
        _text("target", self.target)
        if self.prior_attempts < 0:
            raise MediaQualityControlError("prior_attempts must not be negative")
        if self.max_attempts <= 0:
            raise MediaQualityControlError("max_attempts must be positive")
        if self.prior_attempts >= self.max_attempts:
            raise MediaQualityControlError(
                f"repair attempts exhausted for target: {self.target}"
            )


@dataclass(frozen=True, slots=True)
class MediaRepairPlan:
    plan_id: str
    artifact_sha256: str
    targets: tuple[RepairTarget, ...]


class BoundedMediaRepairPlanner:
    """Plan repairs only for evidence-backed failed targets."""

    def __init__(self, *, max_attempts_per_target: int = 2) -> None:
        if max_attempts_per_target <= 0:
            raise MediaQualityControlError("max_attempts_per_target must be positive")
        self._max_attempts = max_attempts_per_target

    def plan(
        self,
        evidence: ContinuityQualityEvidence,
        *,
        prior_attempts: dict[str, int] | None = None,
    ) -> MediaRepairPlan | None:
        if evidence.passed:
            return None
        attempts = prior_attempts or {}
        unknown = set(attempts) - set(evidence.failed_targets)
        if unknown:
            raise MediaQualityControlError(
                "repair attempt state contains targets that did not fail"
            )
        targets = tuple(
            RepairTarget(
                target=target,
                prior_attempts=attempts.get(target, 0),
                max_attempts=self._max_attempts,
            )
            for target in sorted(set(evidence.failed_targets))
        )
        material = "|".join(
            [evidence.artifact_sha256]
            + [f"{item.target}:{item.prior_attempts}:{item.max_attempts}" for item in targets]
        )
        return MediaRepairPlan(
            plan_id=f"media-repair-{sha256(material.encode()).hexdigest()[:16]}",
            artifact_sha256=evidence.artifact_sha256,
            targets=targets,
        )


def continuity_acceptance_check(
    evidence: ContinuityQualityEvidence,
    *,
    expected_artifact_sha256: str,
) -> FinalEpisodeQualityCheck:
    """Project continuity into the existing final acceptance authority."""

    _sha256("expected_artifact_sha256", expected_artifact_sha256)
    if evidence.artifact_sha256 != expected_artifact_sha256:
        raise MediaQualityControlError(
            "continuity evidence does not match the exact final artifact"
        )
    return FinalEpisodeQualityCheck(
        check_code="continuity_quality",
        passed=evidence.passed,
        evidence_id=evidence.evidence_ref,
        detail=(
            f"continuity score {format(evidence.score, '.12g')} against threshold "
            f"{format(evidence.threshold, '.12g')}"
        ),
    )


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise MediaQualityControlError(f"{name} must be non-blank and trimmed")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64:
        raise MediaQualityControlError(f"{name} must be SHA-256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise MediaQualityControlError(f"{name} must be SHA-256 hex") from exc
