"""Deterministic research pipeline for ILAIOS Video Automation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import ResearchPacket, VideoJob


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


def _normalize_unique(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values:
        _validate_text(field_name, value)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class ResearchInput:
    """Raw, provider-neutral research inputs for one video job."""

    topic_summary: str
    verified_facts: tuple[str, ...]
    source_references: tuple[str, ...]
    key_claims: tuple[str, ...] = ()
    statistics: tuple[str, ...] = ()
    relevant_dates: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    uncertain_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_text("topic_summary", self.topic_summary)


@dataclass(frozen=True, slots=True)
class ResearchPolicy:
    """Validation thresholds for research completion."""

    minimum_verified_facts: int = 1
    minimum_source_references: int = 1
    reject_uncertain_claims: bool = False

    def __post_init__(self) -> None:
        if self.minimum_verified_facts < 0:
            raise ValueError("minimum_verified_facts must be >= 0")
        if self.minimum_source_references < 0:
            raise ValueError("minimum_source_references must be >= 0")


@dataclass(frozen=True, slots=True)
class ResearchValidation:
    """Deterministic research validation result."""

    passed: bool
    reasons: tuple[str, ...]


class ResearchPipeline:
    """Normalize, validate, and materialize research for a VideoJob."""

    def __init__(self, policy: ResearchPolicy | None = None) -> None:
        self._policy = policy or ResearchPolicy()

    @property
    def policy(self) -> ResearchPolicy:
        return self._policy

    def validate(self, research: ResearchInput) -> ResearchValidation:
        """Validate research against configured thresholds."""

        facts = _normalize_unique(
            research.verified_facts,
            field_name="verified fact",
        )
        sources = _normalize_unique(
            research.source_references,
            field_name="source reference",
        )
        uncertain = _normalize_unique(
            research.uncertain_claims,
            field_name="uncertain claim",
        )

        reasons: list[str] = []

        if len(facts) < self._policy.minimum_verified_facts:
            reasons.append(
                "insufficient verified facts: "
                f"{len(facts)} < {self._policy.minimum_verified_facts}"
            )

        if len(sources) < self._policy.minimum_source_references:
            reasons.append(
                "insufficient source references: "
                f"{len(sources)} < {self._policy.minimum_source_references}"
            )

        if self._policy.reject_uncertain_claims and uncertain:
            reasons.append("uncertain claims are not allowed by research policy")

        return ResearchValidation(
            passed=not reasons,
            reasons=tuple(reasons),
        )

    def build_packet(
        self,
        *,
        job: VideoJob,
        research: ResearchInput,
    ) -> ResearchPacket:
        """Build a validated, normalized ResearchPacket for downstream modules."""

        validation = self.validate(research)
        if not validation.passed:
            joined = "; ".join(validation.reasons)
            raise ValueError(f"research validation failed: {joined}")

        return ResearchPacket(
            job_id=job.job_id,
            topic_summary=research.topic_summary,
            verified_facts=_normalize_unique(
                research.verified_facts,
                field_name="verified fact",
            ),
            source_references=_normalize_unique(
                research.source_references,
                field_name="source reference",
            ),
            key_claims=_normalize_unique(
                research.key_claims,
                field_name="key claim",
            ),
            statistics=_normalize_unique(
                research.statistics,
                field_name="statistic",
            ),
            relevant_dates=_normalize_unique(
                research.relevant_dates,
                field_name="relevant date",
            ),
            entities=_normalize_unique(
                research.entities,
                field_name="entity",
            ),
            risks=_normalize_unique(
                research.risks,
                field_name="risk",
            ),
            uncertain_claims=_normalize_unique(
                research.uncertain_claims,
                field_name="uncertain claim",
            ),
        )
