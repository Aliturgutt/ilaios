"""Unified media acceptance evidence over existing factory-specific QA.

This layer does not replace VideoQualityFoundation or Image Factory evaluators.
It aggregates their externally produced observations, adds continuity as a first-
class domain, and enforces a bounded repair budget before final acceptance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256


class MediaQualityError(ValueError):
    """Raised when media acceptance or repair evidence is incomplete."""


class MediaKind(str, Enum):
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"


class MediaQualityDomain(str, Enum):
    VISUAL = "VISUAL"
    AUDIO = "AUDIO"
    BRAND = "BRAND"
    CONTINUITY = "CONTINUITY"
    TECHNICAL = "TECHNICAL"


@dataclass(frozen=True, slots=True)
class MediaQualityObservation:
    observation_id: str
    domain: MediaQualityDomain
    artifact_sha256: str
    producer_id: str
    observer_id: str
    score: float
    threshold: float
    evidence_ref: str
    repair_target: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("observation_id", self.observation_id),
            ("producer_id", self.producer_id),
            ("observer_id", self.observer_id),
            ("evidence_ref", self.evidence_ref),
        ):
            _text(name, value)
        _sha256("artifact_sha256", self.artifact_sha256)
        if self.producer_id == self.observer_id:
            raise MediaQualityError("media quality observer must be independent from producer")
        if not 0 <= self.score <= 1 or not 0 <= self.threshold <= 1:
            raise MediaQualityError("media quality score and threshold must be within [0, 1]")
        if self.passed and self.repair_target is not None:
            raise MediaQualityError("passed observation must not request repair")
        if not self.passed:
            if self.repair_target is None:
                raise MediaQualityError("failed observation requires repair_target")
            _text("repair_target", self.repair_target)

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True, slots=True)
class MediaRepairBudget:
    max_total_attempts: int
    max_attempts_per_target: int

    def __post_init__(self) -> None:
        if self.max_total_attempts < 0 or self.max_attempts_per_target < 0:
            raise MediaQualityError("repair budgets must be non-negative")
        if self.max_attempts_per_target > self.max_total_attempts:
            raise MediaQualityError(
                "max_attempts_per_target cannot exceed max_total_attempts"
            )


@dataclass(frozen=True, slots=True)
class MediaRepairAction:
    target: str
    domain: MediaQualityDomain
    attempt: int
    evidence_ref: str

    def __post_init__(self) -> None:
        _text("target", self.target)
        _text("evidence_ref", self.evidence_ref)
        if self.attempt < 1:
            raise MediaQualityError("repair attempt must be positive")


@dataclass(frozen=True, slots=True)
class MediaAcceptanceEvidence:
    acceptance_id: str
    media_kind: MediaKind
    artifact_sha256: str
    accepted: bool
    required_domains: tuple[MediaQualityDomain, ...]
    observations: tuple[MediaQualityObservation, ...]
    repair_plan: tuple[MediaRepairAction, ...]
    aggregate_score: float

    def __post_init__(self) -> None:
        _text("acceptance_id", self.acceptance_id)
        _sha256("artifact_sha256", self.artifact_sha256)
        if not 0 <= self.aggregate_score <= 1:
            raise MediaQualityError("aggregate_score must be within [0, 1]")
        if self.accepted and self.repair_plan:
            raise MediaQualityError("accepted artifact must not contain repair actions")


class MediaAcceptanceGate:
    """Aggregate required domains and produce deterministic bounded repair evidence."""

    def evaluate(
        self,
        *,
        media_kind: MediaKind,
        artifact_sha256: str,
        observations: Sequence[MediaQualityObservation],
        required_domains: Sequence[MediaQualityDomain],
        repair_budget: MediaRepairBudget,
        prior_attempts: Mapping[str, int] | None = None,
    ) -> MediaAcceptanceEvidence:
        _sha256("artifact_sha256", artifact_sha256)
        required = tuple(required_domains)
        if not required or len(required) != len(set(required)):
            raise MediaQualityError("required media quality domains must be non-empty and unique")
        items = tuple(sorted(observations, key=lambda item: item.domain.value))
        if len(items) != len(required):
            raise MediaQualityError("exactly one observation is required per requested domain")
        if {item.domain for item in items} != set(required):
            raise MediaQualityError("media quality observations do not match required domains")
        ids = [item.observation_id for item in items]
        if len(ids) != len(set(ids)):
            raise MediaQualityError("media quality observation ids must be unique")
        for item in items:
            if item.artifact_sha256 != artifact_sha256:
                raise MediaQualityError("quality observation artifact identity mismatch")

        failures = tuple(item for item in items if not item.passed)
        attempts = {} if prior_attempts is None else dict(prior_attempts)
        if any(value < 0 for value in attempts.values()):
            raise MediaQualityError("prior repair attempts must be non-negative")
        known_targets = {item.repair_target for item in failures if item.repair_target is not None}
        unknown_targets = set(attempts) - known_targets
        if unknown_targets:
            raise MediaQualityError(
                "repair history references unknown targets: " + ", ".join(sorted(unknown_targets))
            )

        repair_plan: list[MediaRepairAction] = []
        consumed = sum(attempts.values())
        for item in failures:
            target = item.repair_target
            if target is None:
                raise MediaQualityError("failed observation missing repair target")
            previous = attempts.get(target, 0)
            if previous >= repair_budget.max_attempts_per_target:
                continue
            if consumed + len(repair_plan) >= repair_budget.max_total_attempts:
                break
            repair_plan.append(
                MediaRepairAction(
                    target=target,
                    domain=item.domain,
                    attempt=previous + 1,
                    evidence_ref=item.evidence_ref,
                )
            )

        accepted = not failures
        aggregate = sum(item.score for item in items) / len(items)
        acceptance_id = _acceptance_id(
            media_kind=media_kind,
            artifact_sha256=artifact_sha256,
            required_domains=required,
            observations=items,
            repair_plan=tuple(repair_plan),
        )
        return MediaAcceptanceEvidence(
            acceptance_id=acceptance_id,
            media_kind=media_kind,
            artifact_sha256=artifact_sha256,
            accepted=accepted,
            required_domains=required,
            observations=items,
            repair_plan=tuple(repair_plan),
            aggregate_score=aggregate,
        )


def video_required_domains() -> tuple[MediaQualityDomain, ...]:
    return (
        MediaQualityDomain.VISUAL,
        MediaQualityDomain.AUDIO,
        MediaQualityDomain.BRAND,
        MediaQualityDomain.CONTINUITY,
        MediaQualityDomain.TECHNICAL,
    )


def image_required_domains(*, continuity_required: bool) -> tuple[MediaQualityDomain, ...]:
    domains = [
        MediaQualityDomain.VISUAL,
        MediaQualityDomain.BRAND,
        MediaQualityDomain.TECHNICAL,
    ]
    if continuity_required:
        domains.append(MediaQualityDomain.CONTINUITY)
    return tuple(domains)


def _acceptance_id(
    *,
    media_kind: MediaKind,
    artifact_sha256: str,
    required_domains: tuple[MediaQualityDomain, ...],
    observations: tuple[MediaQualityObservation, ...],
    repair_plan: tuple[MediaRepairAction, ...],
) -> str:
    material = [media_kind.value, artifact_sha256]
    material.extend(domain.value for domain in required_domains)
    material.extend(
        "|".join(
            (
                item.observation_id,
                item.domain.value,
                item.producer_id,
                item.observer_id,
                format(item.score, ".12g"),
                format(item.threshold, ".12g"),
                item.evidence_ref,
                item.repair_target or "",
            )
        )
        for item in observations
    )
    material.extend(
        f"{item.domain.value}|{item.target}|{item.attempt}|{item.evidence_ref}"
        for item in repair_plan
    )
    return "media-acceptance-" + sha256("\n".join(material).encode()).hexdigest()[:24]


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise MediaQualityError(f"{name} must be non-blank normalized text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise MediaQualityError(f"{name} must be lowercase SHA-256")
