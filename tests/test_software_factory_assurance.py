from __future__ import annotations

from pathlib import Path

import pytest

from services.software_factory_assurance import (
    AssuranceDisposition,
    AssuranceError,
    CANONICAL_DOCUMENTS,
    DocumentationState,
    RED_TEAM_SCENARIOS,
    SkillEvalOutcome,
    SoftwareFactoryAssurance,
)
from services.software_factory_skills import SkillRegistry, default_skills_root

BASE = "c" * 40
HEAD = "d" * 40
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_sf29_canonical_registry_structural_audit_passes() -> None:
    registry = SkillRegistry(default_skills_root(REPOSITORY_ROOT))
    report = SoftwareFactoryAssurance().sf29_registry_self_audit(
        REPOSITORY_ROOT, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is AssuranceDisposition.PASS
    assert report.subjects_evaluated == len(registry.skill_ids)
    assert report.repository_mutation_authorized is False


def test_sf29_complete_declared_eval_matrix_can_be_reconciled() -> None:
    registry = SkillRegistry(default_skills_root(REPOSITORY_ROOT))
    outcomes: list[SkillEvalOutcome] = []
    for skill_id in registry.skill_ids:
        package = registry.resolve(skill_id)
        for case in package.evals:
            kind = case["kind"]
            case_id = case["id"]
            expected = case["expected"]
            assert isinstance(kind, str)
            assert isinstance(case_id, str)
            assert isinstance(expected, str)
            outcomes.append(
                SkillEvalOutcome(
                    skill_id=skill_id,
                    kind=kind,
                    case_id=case_id,
                    expected=expected,
                    actual=expected,
                    runner_id="pytest-assurance-v1",
                    skill_version=package.manifest.version,
                )
            )

    report = SoftwareFactoryAssurance().sf29_skill_evaluation(
        REPOSITORY_ROOT, outcomes, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is AssuranceDisposition.PASS
    assert report.subjects_evaluated == len(outcomes)


def test_sf29_failed_or_missing_eval_fails_closed() -> None:
    registry = SkillRegistry(default_skills_root(REPOSITORY_ROOT))
    package = registry.resolve("sf-api-contract")
    case = package.evals[0]
    outcome = SkillEvalOutcome(
        skill_id="sf-api-contract",
        kind=str(case["kind"]),
        case_id=str(case["id"]),
        expected=str(case["expected"]),
        actual="WRONG",
        runner_id="pytest-assurance-v1",
        skill_version=package.manifest.version,
    )
    report = SoftwareFactoryAssurance().sf29_skill_evaluation(
        REPOSITORY_ROOT, (outcome,), base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is AssuranceDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "SF29-EVAL-FAIL" in identifiers
    assert "SF29-MISSING-RESULT" in identifiers


def test_sf30_builtin_adversarial_matrix_blocks_every_attack() -> None:
    report = SoftwareFactoryAssurance().sf30_builtin_matrix(
        base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is AssuranceDisposition.PASS
    assert report.subjects_evaluated == len(RED_TEAM_SCENARIOS)


def test_sf30_policy_escape_fails_closed() -> None:
    actual = {
        scenario.scenario_id: AssuranceDisposition.BLOCK
        for scenario in RED_TEAM_SCENARIOS
    }
    actual["RT-DIRECT-MASTER"] = AssuranceDisposition.PASS
    report = SoftwareFactoryAssurance().sf30_red_team(
        actual, base_sha=BASE, head_sha=HEAD
    )
    assert report.disposition is AssuranceDisposition.BLOCK
    assert any(
        item.finding_id == "SF30-POLICY-ESCAPE" for item in report.findings
    )


def test_sf31_canonical_document_set_and_truth_boundary_pass() -> None:
    report = SoftwareFactoryAssurance().sf31_documentation_sync(
        REPOSITORY_ROOT,
        DocumentationState(
            observed_truth_separated=True,
            mutable_status_outside_normative_authority=True,
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is AssuranceDisposition.PASS
    assert report.subjects_evaluated == len(CANONICAL_DOCUMENTS)


def test_sf31_unsupported_claims_and_duplicate_authority_block() -> None:
    report = SoftwareFactoryAssurance().sf31_documentation_sync(
        REPOSITORY_ROOT,
        DocumentationState(
            observed_truth_separated=False,
            mutable_status_outside_normative_authority=False,
            unsupported_production_claims=("all capabilities deployed",),
            duplicate_authority_claims=("Core 2",),
        ),
        base_sha=BASE,
        head_sha=HEAD,
    )
    assert report.disposition is AssuranceDisposition.BLOCK
    identifiers = {item.finding_id for item in report.findings}
    assert "SF31-TRUTH-BOUNDARY" in identifiers
    assert "SF31-MUTABLE-STATUS" in identifiers
    assert "SF31-UNSUPPORTED-CLAIM" in identifiers
    assert "SF31-DUPLICATE-AUTHORITY" in identifiers


def test_assurance_sha_validation_is_fail_closed() -> None:
    with pytest.raises(AssuranceError, match="40-character SHA"):
        SoftwareFactoryAssurance().sf30_builtin_matrix(
            base_sha="master", head_sha=HEAD
        )
