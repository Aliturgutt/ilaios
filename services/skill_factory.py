"""Evidence-first ILAIOS skill generation lifecycle bound to the canonical runtime."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from services.runtime.execution import GovernedRuntime


class SkillFactoryError(ValueError):
    """Candidate or evaluation state is invalid."""


class SkillPromotionError(PermissionError):
    """A candidate failed closed before canonical runtime promotion."""


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    skill_id: str
    instructions: str
    source_trace_digest: str
    required_authorities: frozenset[str]

    def __post_init__(self) -> None:
        if not self.skill_id.startswith("ilaios.skill."):
            raise SkillFactoryError("skill IDs must use the ilaios.skill namespace")
        if not self.instructions.strip():
            raise SkillFactoryError("skill instructions are required")
        if len(self.source_trace_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_trace_digest
        ):
            raise SkillFactoryError("source trace must use a lowercase SHA-256 digest")
        if not self.required_authorities or any(
            not authority.strip() for authority in self.required_authorities
        ):
            raise SkillFactoryError("bounded runtime authorities are required")

    @property
    def artifact_content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"

    @property
    def artifact_digest(self) -> str:
        return sha256(self.artifact_content).hexdigest()


@dataclass(frozen=True, slots=True)
class SkillScenarioResult:
    scenario_id: str
    assertions_passed: int
    assertions_total: int

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise SkillFactoryError("scenario identity is required")
        if self.assertions_total <= 0 or not 0 <= self.assertions_passed <= self.assertions_total:
            raise SkillFactoryError("invalid scenario assertion counts")

    @property
    def passed(self) -> bool:
        return self.assertions_passed == self.assertions_total


@dataclass(frozen=True, slots=True)
class SkillEvaluation:
    candidate_digest: str
    model_id: str
    baseline_pass_rate: float
    candidate_pass_rate: float
    scenarios: tuple[SkillScenarioResult, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.candidate_digest) != 64 or not self.model_id.strip():
            raise SkillFactoryError("candidate digest and model identity are required")
        if not 0.0 <= self.baseline_pass_rate <= 1.0 or not 0.0 <= self.candidate_pass_rate <= 1.0:
            raise SkillFactoryError("pass rates must be between zero and one")
        if not self.scenarios:
            raise SkillFactoryError("evaluation scenarios are required")
        if not self.evidence_ids or any(not evidence_id.strip() for evidence_id in self.evidence_ids):
            raise SkillFactoryError("evaluation evidence is required")

    @property
    def regression_delta(self) -> float:
        return self.candidate_pass_rate - self.baseline_pass_rate


@dataclass(frozen=True, slots=True)
class PromotionRequirements:
    minimum_scenarios: int = 3
    minimum_pass_rate: float = 0.90
    minimum_regression_delta: float = 0.0


class PromotionGovernance(Protocol):
    def authorize_promotion(self, *, candidate: SkillCandidate, evaluation: SkillEvaluation) -> str: ...


class PromotionEvidence(Protocol):
    def record_promotion_authorization(
        self,
        *,
        candidate: SkillCandidate,
        evaluation: SkillEvaluation,
        governance_evidence_id: str,
    ) -> str: ...


class SkillProvisioner(Protocol):
    def ensure_skill(self, skill_id: str, content: bytes, authorities: frozenset[str]) -> str: ...


class CanonicalRuntimeSkillProvisioner:
    """Thin adapter into the one canonical GovernedRuntime skill store."""

    def __init__(self, runtime: GovernedRuntime) -> None:
        self._runtime = runtime

    def ensure_skill(self, skill_id: str, content: bytes, authorities: frozenset[str]) -> str:
        return self._runtime.ensure_skill(skill_id, content, authorities)


@dataclass(frozen=True, slots=True)
class PromotedSkill:
    candidate: SkillCandidate
    evaluation: SkillEvaluation
    governance_evidence_id: str
    authorization_evidence_id: str
    runtime_digest: str


class SkillPromotionGate:
    """Fail closed before provisioning immutable content into the canonical runtime."""

    def __init__(
        self,
        governance: PromotionGovernance,
        evidence: PromotionEvidence,
        provisioner: SkillProvisioner,
        requirements: PromotionRequirements | None = None,
    ) -> None:
        self._governance = governance
        self._evidence = evidence
        self._provisioner = provisioner
        self._requirements = requirements or PromotionRequirements()

    def promote(self, candidate: SkillCandidate, evaluation: SkillEvaluation) -> PromotedSkill:
        requirements = self._requirements
        if requirements.minimum_scenarios <= 0:
            raise SkillFactoryError("minimum scenarios must be positive")
        if not 0.0 <= requirements.minimum_pass_rate <= 1.0:
            raise SkillFactoryError("minimum pass rate must be between zero and one")
        if evaluation.candidate_digest != candidate.artifact_digest:
            raise SkillPromotionError("evaluation does not belong to candidate content")
        if len(evaluation.scenarios) < requirements.minimum_scenarios:
            raise SkillPromotionError("insufficient evaluation scenarios")
        if evaluation.candidate_pass_rate < requirements.minimum_pass_rate:
            raise SkillPromotionError("candidate pass rate is below promotion threshold")
        if evaluation.regression_delta < requirements.minimum_regression_delta:
            raise SkillPromotionError("candidate regresses against baseline")
        if any(not scenario.passed for scenario in evaluation.scenarios):
            raise SkillPromotionError("all promotion scenarios must pass")

        governance_evidence_id = self._governance.authorize_promotion(
            candidate=candidate, evaluation=evaluation
        )
        if not governance_evidence_id:
            raise SkillPromotionError("policy/approval evidence is required")
        authorization_evidence_id = self._evidence.record_promotion_authorization(
            candidate=candidate,
            evaluation=evaluation,
            governance_evidence_id=governance_evidence_id,
        )
        if not authorization_evidence_id:
            raise SkillPromotionError("promotion authorization evidence is required")

        runtime_digest = self._provisioner.ensure_skill(
            candidate.skill_id,
            candidate.artifact_content,
            candidate.required_authorities,
        )
        if runtime_digest != candidate.artifact_digest:
            raise SkillPromotionError("canonical runtime digest diverged from candidate")
        return PromotedSkill(
            candidate,
            evaluation,
            governance_evidence_id,
            authorization_evidence_id,
            runtime_digest,
        )
