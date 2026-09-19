"""ILAIOS-native skill candidate, evaluation, regression, and promotion controls.

This module is intentionally additive. It does not execute tools or providers and it
cannot promote a skill without governance and evidence attestations supplied by the
canonical platform boundaries.

Canonical skill taxonomy/package truth lives in ``services.skill_taxonomy`` and
``services.skill_engineering_catalog``. The promotion registry in this module stores
only immutable promotion records; it is not a second runtime SkillRegistry, package
catalog, capability registry, router, policy authority, or maturity authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Protocol


class SkillFactoryError(ValueError):
    """Skill lifecycle input or promotion-record state is invalid."""


class SkillPromotionError(PermissionError):
    """A candidate failed closed at the promotion boundary."""


class SkillPromotionState(str, Enum):
    """Promotion workflow state, deliberately separate from canonical maturity."""

    CANDIDATE = "candidate"
    EVALUATED = "evaluated"
    PROMOTED = "promoted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    skill_id: str
    version: str
    instructions: str
    source_trace_digest: str
    required_capabilities: frozenset[str]
    required_permissions: frozenset[str]

    def __post_init__(self) -> None:
        if not self.skill_id.startswith("ilaios.skill."):
            raise SkillFactoryError("skill IDs must use the ilaios.skill namespace")
        if not self.version.strip() or not self.instructions.strip():
            raise SkillFactoryError("version and instructions are required")
        if len(self.source_trace_digest) != 64:
            raise SkillFactoryError("source trace must be represented by a SHA-256 digest")

    @property
    def package_digest(self) -> str:
        payload = "\n".join(
            (
                self.skill_id,
                self.version,
                self.instructions,
                self.source_trace_digest,
                ",".join(sorted(self.required_capabilities)),
                ",".join(sorted(self.required_permissions)),
            )
        )
        return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SkillScenarioResult:
    scenario_id: str
    passed: bool
    assertions_passed: int
    assertions_total: int

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise SkillFactoryError("scenario identity is required")
        if self.assertions_total <= 0:
            raise SkillFactoryError("scenario must contain at least one assertion")
        if not 0 <= self.assertions_passed <= self.assertions_total:
            raise SkillFactoryError("invalid assertion counts")
        if self.passed != (self.assertions_passed == self.assertions_total):
            raise SkillFactoryError("scenario pass state must match assertion results")


@dataclass(frozen=True, slots=True)
class SkillEvaluation:
    candidate_digest: str
    model_id: str
    baseline_pass_rate: float
    candidate_pass_rate: float
    scenarios: tuple[SkillScenarioResult, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.candidate_digest) != 64 or not self.model_id:
            raise SkillFactoryError("candidate digest and model identity are required")
        if not 0.0 <= self.baseline_pass_rate <= 1.0:
            raise SkillFactoryError("baseline pass rate must be between zero and one")
        if not 0.0 <= self.candidate_pass_rate <= 1.0:
            raise SkillFactoryError("candidate pass rate must be between zero and one")
        if not self.scenarios:
            raise SkillFactoryError("evaluation scenarios are required")
        if not self.evidence_ids or any(not item for item in self.evidence_ids):
            raise SkillFactoryError("evaluation evidence is required")

    @property
    def regression_delta(self) -> float:
        return self.candidate_pass_rate - self.baseline_pass_rate


@dataclass(frozen=True, slots=True)
class PromotionRequirements:
    minimum_scenarios: int = 3
    minimum_pass_rate: float = 0.90
    minimum_regression_delta: float = 0.0

    def __post_init__(self) -> None:
        if self.minimum_scenarios <= 0:
            raise SkillFactoryError("minimum scenarios must be positive")
        if not 0.0 <= self.minimum_pass_rate <= 1.0:
            raise SkillFactoryError("minimum pass rate must be between zero and one")


class PromotionGovernance(Protocol):
    """Canonical policy/approval boundary required for promotion."""

    def authorize_promotion(
        self, *, candidate: SkillCandidate, evaluation: SkillEvaluation
    ) -> str: ...


class PromotionEvidence(Protocol):
    """Canonical audit/evidence boundary required for promotion."""

    def record_promotion(
        self,
        *,
        candidate: SkillCandidate,
        evaluation: SkillEvaluation,
        governance_evidence_id: str,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class PromotedSkill:
    candidate: SkillCandidate
    evaluation: SkillEvaluation
    governance_evidence_id: str
    promotion_evidence_id: str
    promotion_state: SkillPromotionState = SkillPromotionState.PROMOTED


class SkillPromotionRegistry:
    """Immutable promotion records only; never canonical runtime skill identity truth."""

    def __init__(self) -> None:
        self._skills: dict[tuple[str, str], PromotedSkill] = {}

    def register(self, promoted: PromotedSkill) -> None:
        key = (promoted.candidate.skill_id, promoted.candidate.version)
        existing = self._skills.get(key)
        if existing is not None:
            if existing.candidate.package_digest != promoted.candidate.package_digest:
                raise SkillFactoryError("skill version is immutable after promotion")
            return
        self._skills[key] = promoted

    def get(self, skill_id: str, version: str) -> PromotedSkill:
        try:
            return self._skills[(skill_id, version)]
        except KeyError as exc:
            raise KeyError(f"unknown promoted skill: {skill_id}@{version}") from exc

    def all(self) -> tuple[PromotedSkill, ...]:
        return tuple(self._skills[key] for key in sorted(self._skills))


class SkillPromotionGate:
    """Evidence-first, fail-closed candidate promotion."""

    def __init__(
        self,
        governance: PromotionGovernance,
        evidence: PromotionEvidence,
        registry: SkillPromotionRegistry,
        requirements: PromotionRequirements | None = None,
    ) -> None:
        self._governance = governance
        self._evidence = evidence
        self._registry = registry
        self._requirements = requirements or PromotionRequirements()

    def promote(
        self, candidate: SkillCandidate, evaluation: SkillEvaluation
    ) -> PromotedSkill:
        if evaluation.candidate_digest != candidate.package_digest:
            raise SkillPromotionError("evaluation does not belong to candidate package")
        if len(evaluation.scenarios) < self._requirements.minimum_scenarios:
            raise SkillPromotionError("insufficient evaluation scenarios")
        if evaluation.candidate_pass_rate < self._requirements.minimum_pass_rate:
            raise SkillPromotionError("candidate pass rate is below promotion threshold")
        if evaluation.regression_delta < self._requirements.minimum_regression_delta:
            raise SkillPromotionError("candidate regresses against baseline")
        if any(not result.passed for result in evaluation.scenarios):
            raise SkillPromotionError("all promotion scenarios must pass")

        governance_evidence_id = self._governance.authorize_promotion(
            candidate=candidate, evaluation=evaluation
        )
        if not governance_evidence_id:
            raise SkillPromotionError("policy/approval evidence is required")
        promotion_evidence_id = self._evidence.record_promotion(
            candidate=candidate,
            evaluation=evaluation,
            governance_evidence_id=governance_evidence_id,
        )
        if not promotion_evidence_id:
            raise SkillPromotionError("promotion evidence record is required")

        promoted = PromotedSkill(
            candidate=candidate,
            evaluation=evaluation,
            governance_evidence_id=governance_evidence_id,
            promotion_evidence_id=promotion_evidence_id,
        )
        self._registry.register(promoted)
        return promoted
