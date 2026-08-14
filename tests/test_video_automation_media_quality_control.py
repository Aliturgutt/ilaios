from __future__ import annotations

import pytest

from src.video_automation.media_quality_control import (
    BoundedMediaRepairPlanner,
    ContinuityQualityEvidence,
    MediaQualityControlError,
    continuity_acceptance_check,
)


def _failed() -> ContinuityQualityEvidence:
    return ContinuityQualityEvidence(
        artifact_sha256="a" * 64,
        score=0.6,
        threshold=0.85,
        evaluator_id="continuity-evaluator-001",
        evidence_ref="evidence://continuity/001",
        failed_targets=("character_identity", "last_scene_transition"),
    )


def test_continuity_check_is_bound_to_exact_final_artifact() -> None:
    check = continuity_acceptance_check(
        ContinuityQualityEvidence(
            artifact_sha256="a" * 64,
            score=0.95,
            threshold=0.85,
            evaluator_id="continuity-evaluator-001",
            evidence_ref="evidence://continuity/accepted",
        ),
        expected_artifact_sha256="a" * 64,
    )
    assert check.check_code == "continuity_quality"
    assert check.passed

    with pytest.raises(MediaQualityControlError, match="exact final artifact"):
        continuity_acceptance_check(
            _failed(), expected_artifact_sha256="b" * 64
        )


def test_repair_planner_targets_only_evidence_backed_failures() -> None:
    plan = BoundedMediaRepairPlanner(max_attempts_per_target=2).plan(
        _failed(), prior_attempts={"character_identity": 1}
    )
    assert plan is not None
    assert [item.target for item in plan.targets] == [
        "character_identity",
        "last_scene_transition",
    ]
    assert plan.targets[0].prior_attempts == 1
    assert plan.targets[1].prior_attempts == 0


def test_repair_planner_rejects_unrelated_target_and_exhaustion() -> None:
    planner = BoundedMediaRepairPlanner(max_attempts_per_target=2)
    with pytest.raises(MediaQualityControlError, match="did not fail"):
        planner.plan(_failed(), prior_attempts={"unrelated": 1})
    with pytest.raises(MediaQualityControlError, match="attempts exhausted"):
        planner.plan(_failed(), prior_attempts={"character_identity": 2})


def test_passing_continuity_has_no_repair_plan() -> None:
    evidence = ContinuityQualityEvidence(
        artifact_sha256="c" * 64,
        score=0.9,
        threshold=0.85,
        evaluator_id="continuity-evaluator-001",
        evidence_ref="evidence://continuity/pass",
    )
    assert BoundedMediaRepairPlanner().plan(evidence) is None
