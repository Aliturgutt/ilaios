"""Skill Factory lifecycle and canonical runtime integration proofs."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pytest

from services.runtime.execution import GovernedRuntime
from services.runtime.routing import RuntimeError as GovernedRuntimeError
from services.skill_factory import (
    CanonicalRuntimeSkillProvisioner,
    SkillCandidate,
    SkillEvaluation,
    SkillPromotionError,
    SkillPromotionGate,
    SkillScenarioResult,
)


@dataclass
class FakeGovernance:
    evidence_id: str = "governance-1"
    calls: list[str] = field(default_factory=list)

    def authorize_promotion(self, *, candidate: SkillCandidate, evaluation: SkillEvaluation) -> str:
        self.calls.append(candidate.artifact_digest)
        return self.evidence_id


@dataclass
class FakeEvidence:
    evidence_id: str = "authorization-1"
    calls: list[str] = field(default_factory=list)

    def record_promotion_authorization(
        self,
        *,
        candidate: SkillCandidate,
        evaluation: SkillEvaluation,
        governance_evidence_id: str,
    ) -> str:
        self.calls.append(f"{candidate.artifact_digest}:{governance_evidence_id}")
        return self.evidence_id


@dataclass
class FakeProvisioner:
    calls: list[str] = field(default_factory=list)

    def ensure_skill(self, skill_id: str, content: bytes, authorities: frozenset[str]) -> str:
        self.calls.append(skill_id)
        return sha256(content).hexdigest()


def candidate(instructions: str = "Create a bounded skill from approved evidence.") -> SkillCandidate:
    return SkillCandidate(
        "ilaios.skill.engineering.create.v1",
        instructions,
        sha256(b"trace").hexdigest(),
        frozenset({"workflow.plan"}),
    )


def evaluation(item: SkillCandidate, *, baseline: float = 0.8, result: float = 1.0) -> SkillEvaluation:
    scenarios = tuple(SkillScenarioResult(f"scenario-{index}", 2, 2) for index in range(3))
    return SkillEvaluation(item.artifact_digest, "test-model", baseline, result, scenarios, ("eval-1",))


def test_regression_fails_before_governance_or_runtime() -> None:
    item = candidate()
    governance = FakeGovernance()
    evidence = FakeEvidence()
    provisioner = FakeProvisioner()
    gate = SkillPromotionGate(governance, evidence, provisioner)
    with pytest.raises(SkillPromotionError, match="regresses"):
        gate.promote(item, evaluation(item, baseline=1.0, result=0.95))
    assert governance.calls == []
    assert evidence.calls == []
    assert provisioner.calls == []


def test_missing_policy_approval_evidence_fails_closed() -> None:
    item = candidate()
    provisioner = FakeProvisioner()
    with pytest.raises(SkillPromotionError, match="policy/approval"):
        SkillPromotionGate(FakeGovernance(""), FakeEvidence(), provisioner).promote(item, evaluation(item))
    assert provisioner.calls == []


def test_missing_authorization_evidence_fails_closed_before_runtime() -> None:
    item = candidate()
    provisioner = FakeProvisioner()
    with pytest.raises(SkillPromotionError, match="authorization evidence"):
        SkillPromotionGate(FakeGovernance(), FakeEvidence(""), provisioner).promote(item, evaluation(item))
    assert provisioner.calls == []


def _runtime_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE runtime_skills (skill_id TEXT PRIMARY KEY, digest TEXT NOT NULL, authorities_json TEXT NOT NULL, content BLOB NOT NULL)"
        )


def test_promotion_provisions_exact_content_into_canonical_runtime(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    _runtime_database(database)
    runtime = GovernedRuntime(database)
    item = candidate()
    promoted = SkillPromotionGate(
        FakeGovernance(), FakeEvidence(), CanonicalRuntimeSkillProvisioner(runtime)
    ).promote(item, evaluation(item))
    assert promoted.runtime_digest == item.artifact_digest
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT digest, authorities_json, content FROM runtime_skills WHERE skill_id = ?",
            (item.skill_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == item.artifact_digest
    assert row[2] == item.artifact_content


def test_canonical_runtime_rejects_content_drift_for_same_skill_id(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    _runtime_database(database)
    runtime = GovernedRuntime(database)
    gate = SkillPromotionGate(FakeGovernance(), FakeEvidence(), CanonicalRuntimeSkillProvisioner(runtime))
    original = candidate()
    gate.promote(original, evaluation(original))
    changed = candidate("Changed instructions under an already promoted identity.")
    with pytest.raises(GovernedRuntimeError, match="drifted"):
        gate.promote(changed, evaluation(changed))
