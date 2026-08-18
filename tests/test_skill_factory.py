"""ILAIOS-native skill factory lifecycle proofs."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pytest

from services.skill_factory import (
    PromotedSkill,
    SkillCandidate,
    SkillEvaluation,
    SkillFactoryError,
    SkillPromotionError,
    SkillPromotionGate,
    SkillPromotionRegistry,
    SkillPromotionState,
    SkillScenarioResult,
)


@dataclass
class FakeGovernance:
    evidence_id: str = "gov-evidence-1"
    calls: list[str] = field(default_factory=list)

    def authorize_promotion(
        self, *, candidate: SkillCandidate, evaluation: SkillEvaluation
    ) -> str:
        self.calls.append(candidate.package_digest)
        return self.evidence_id


@dataclass
class FakeEvidence:
    evidence_id: str = "promotion-evidence-1"
    calls: list[str] = field(default_factory=list)

    def record_promotion(
        self,
        *,
        candidate: SkillCandidate,
        evaluation: SkillEvaluation,
        governance_evidence_id: str,
    ) -> str:
        self.calls.append(f"{candidate.package_digest}:{governance_evidence_id}")
        return self.evidence_id


def candidate() -> SkillCandidate:
    return SkillCandidate(
        skill_id="ilaios.skill.engineering.create",
        version="1.0.0",
        instructions="Create a bounded ILAIOS-native skill from approved inputs.",
        source_trace_digest=sha256(b"trace-1").hexdigest(),
        required_capabilities=frozenset({"ilaios.capability.policy-governance"}),
        required_permissions=frozenset({"skill.propose"}),
    )


def passing_evaluation(item: SkillCandidate) -> SkillEvaluation:
    scenarios = tuple(
        SkillScenarioResult(
            scenario_id=f"scenario-{index}",
            passed=True,
            assertions_passed=2,
            assertions_total=2,
        )
        for index in range(3)
    )
    return SkillEvaluation(
        candidate_digest=item.package_digest,
        model_id="test-model",
        baseline_pass_rate=0.80,
        candidate_pass_rate=1.0,
        scenarios=scenarios,
        evidence_ids=("eval-evidence-1",),
    )


def test_candidate_identity_is_namespaced_and_immutable_digest_is_stable() -> None:
    item = candidate()
    assert item.skill_id.startswith("ilaios.skill.")
    assert item.package_digest == item.package_digest
    assert len(item.package_digest) == 64


def test_candidate_rejects_non_ilaios_identity() -> None:
    with pytest.raises(SkillFactoryError, match="namespace"):
        SkillCandidate(
            skill_id="thirdparty.skill.create",
            version="1.0.0",
            instructions="x",
            source_trace_digest=sha256(b"trace").hexdigest(),
            required_capabilities=frozenset(),
            required_permissions=frozenset(),
        )


def test_promotion_state_is_not_canonical_maturity() -> None:
    assert SkillPromotionState.PROMOTED.value == "promoted"
    source = (Path(__file__).resolve().parents[1] / "services" / "skill_factory.py").read_text(
        encoding="utf-8"
    )
    assert "class SkillMaturity" not in source
    assert "class SkillRegistry" not in source
    assert "SkillPromotionRegistry" in source
    assert "canonical maturity" in source.casefold()


def test_promotion_requires_matching_evaluation_digest() -> None:
    item = candidate()
    evaluation = passing_evaluation(item)
    wrong = SkillEvaluation(
        candidate_digest=sha256(b"other").hexdigest(),
        model_id=evaluation.model_id,
        baseline_pass_rate=evaluation.baseline_pass_rate,
        candidate_pass_rate=evaluation.candidate_pass_rate,
        scenarios=evaluation.scenarios,
        evidence_ids=evaluation.evidence_ids,
    )
    governance = FakeGovernance()
    evidence = FakeEvidence()
    gate = SkillPromotionGate(governance, evidence, SkillPromotionRegistry())

    with pytest.raises(SkillPromotionError, match="does not belong"):
        gate.promote(item, wrong)
    assert governance.calls == []
    assert evidence.calls == []


def test_promotion_fails_before_governance_when_regression_is_detected() -> None:
    item = candidate()
    baseline = passing_evaluation(item)
    regressed = SkillEvaluation(
        candidate_digest=item.package_digest,
        model_id=baseline.model_id,
        baseline_pass_rate=1.0,
        candidate_pass_rate=0.95,
        scenarios=baseline.scenarios,
        evidence_ids=baseline.evidence_ids,
    )
    governance = FakeGovernance()
    evidence = FakeEvidence()
    gate = SkillPromotionGate(governance, evidence, SkillPromotionRegistry())

    with pytest.raises(SkillPromotionError, match="regresses"):
        gate.promote(item, regressed)
    assert governance.calls == []
    assert evidence.calls == []


def test_promotion_fails_closed_without_policy_approval_evidence() -> None:
    item = candidate()
    governance = FakeGovernance(evidence_id="")
    evidence = FakeEvidence()
    gate = SkillPromotionGate(governance, evidence, SkillPromotionRegistry())

    with pytest.raises(SkillPromotionError, match="policy/approval evidence"):
        gate.promote(item, passing_evaluation(item))
    assert len(governance.calls) == 1
    assert evidence.calls == []


def test_promotion_fails_closed_without_promotion_evidence_record() -> None:
    item = candidate()
    governance = FakeGovernance()
    evidence = FakeEvidence(evidence_id="")
    gate = SkillPromotionGate(governance, evidence, SkillPromotionRegistry())

    with pytest.raises(SkillPromotionError, match="promotion evidence"):
        gate.promote(item, passing_evaluation(item))
    assert len(governance.calls) == 1
    assert len(evidence.calls) == 1


def test_successful_promotion_records_governance_and_evidence_before_registry() -> None:
    item = candidate()
    governance = FakeGovernance()
    evidence = FakeEvidence()
    registry = SkillPromotionRegistry()
    gate = SkillPromotionGate(governance, evidence, registry)

    promoted = gate.promote(item, passing_evaluation(item))

    assert isinstance(promoted, PromotedSkill)
    assert promoted.promotion_state is SkillPromotionState.PROMOTED
    assert promoted.governance_evidence_id == "gov-evidence-1"
    assert promoted.promotion_evidence_id == "promotion-evidence-1"
    assert registry.get(item.skill_id, item.version) == promoted


def test_promoted_skill_version_is_immutable() -> None:
    original = candidate()
    registry = SkillPromotionRegistry()
    gate = SkillPromotionGate(FakeGovernance(), FakeEvidence(), registry)
    gate.promote(original, passing_evaluation(original))

    replacement = SkillCandidate(
        skill_id=original.skill_id,
        version=original.version,
        instructions="Changed instructions under the same version.",
        source_trace_digest=original.source_trace_digest,
        required_capabilities=original.required_capabilities,
        required_permissions=original.required_permissions,
    )
    replacement_promoted = PromotedSkill(
        candidate=replacement,
        evaluation=SkillEvaluation(
            candidate_digest=replacement.package_digest,
            model_id="test-model",
            baseline_pass_rate=0.8,
            candidate_pass_rate=1.0,
            scenarios=tuple(
                SkillScenarioResult(f"scenario-{index}", True, 1, 1)
                for index in range(3)
            ),
            evidence_ids=("eval-evidence-2",),
        ),
        governance_evidence_id="gov-evidence-2",
        promotion_evidence_id="promotion-evidence-2",
    )

    with pytest.raises(SkillFactoryError, match="immutable"):
        registry.register(replacement_promoted)
