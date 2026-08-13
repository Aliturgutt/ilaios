from pathlib import Path

import pytest

from src.video_automation.video_skills import (
    VIDEO_SKILLS,
    CreativeDirection,
    EditKind,
    EditOperation,
    IndependentVideoEvaluator,
    MediaSecurityPolicy,
    QaDomain,
    QaFinding,
    SelectiveRepairController,
    ThumbnailRequest,
    VideoSkillError,
    validate_video_skills,
)

ARTIFACT = "a" * 64


def _findings(failing: QaDomain | None = None) -> tuple[QaFinding, ...]:
    return tuple(
        QaFinding(
            f"finding-{domain.value}",
            domain,
            domain is not failing,
            0.5 if domain is failing else 0.9,
            0.8,
            f"evidence:{domain.value}",
            f"scene:{domain.value}" if domain is failing else None,
        )
        for domain in QaDomain
    )


def test_video_skills_are_canonical_owned_and_digest_bound() -> None:
    validate_video_skills()
    assert len({skill.skill_id for skill in VIDEO_SKILLS}) == len(VIDEO_SKILLS)
    assert all(skill.owner == "ILAIOS" for skill in VIDEO_SKILLS)
    assert all(skill.source_provenance == "ILAIOS-native" for skill in VIDEO_SKILLS)
    assert all(
        skill.capability_id == "ilaios.capability.video-media-factory"
        for skill in VIDEO_SKILLS
    )


def test_editing_never_overwrites_registered_inputs() -> None:
    operation = EditOperation(
        "edit-1", EditKind.TRIM, ("asset-1",), "asset-2", {"end_ms": 1000}
    )
    assert operation.parameters["end_ms"] == 1000
    with pytest.raises(VideoSkillError, match="overwrite"):
        EditOperation("edit-2", EditKind.TRIM, ("asset-1",), "asset-1", {})


def test_creative_direction_requires_continuity_and_palette() -> None:
    direction = CreativeDirection(
        "dir-1",
        "calm",
        "medium",
        "eye-level",
        "dolly",
        "soft",
        ("#000000",),
        "measured",
        ("subject",),
    )
    assert direction.camera_movement == "dolly"
    with pytest.raises(VideoSkillError, match="palette"):
        CreativeDirection(
            "dir-2",
            "calm",
            "medium",
            "eye-level",
            "static",
            "soft",
            (),
            "measured",
            ("subject",),
        )


def test_independent_evaluator_requires_every_domain_and_evidence() -> None:
    evaluator = IndependentVideoEvaluator()
    result = evaluator.evaluate(
        ARTIFACT, _findings(), evaluator_id="ilaios.video.evaluator.v1"
    )
    assert result.passed
    with pytest.raises(VideoSkillError, match="visual, audio"):
        evaluator.evaluate(
            ARTIFACT, _findings()[:-1], evaluator_id="ilaios.video.evaluator.v1"
        )
    with pytest.raises(VideoSkillError, match="visual, audio"):
        evaluator.evaluate(
            ARTIFACT,
            (*_findings(), _findings()[0]),
            evaluator_id="ilaios.video.evaluator.v1",
        )


def test_selective_repair_targets_only_failed_finding_and_is_bounded() -> None:
    evaluation = IndependentVideoEvaluator().evaluate(
        ARTIFACT, _findings(QaDomain.AUDIO), evaluator_id="independent-v1"
    )
    controller = SelectiveRepairController(max_attempts=2)
    repairs = controller.plan(evaluation, {})
    assert [(item.finding_id, item.target, item.attempt) for item in repairs] == [
        ("finding-audio", "scene:audio", 1)
    ]
    with pytest.raises(VideoSkillError, match="exhausted"):
        controller.plan(evaluation, {"finding-audio": 2})
    with pytest.raises(VideoSkillError, match="negative"):
        controller.plan(evaluation, {"finding-audio": -1})


def test_media_security_is_sandboxed_size_bounded_and_provenance_gated(
    tmp_path: Path,
) -> None:
    policy = MediaSecurityPolicy(tmp_path, frozenset({".mp4"}), 1024)
    (tmp_path / "input.mp4").write_bytes(b"video-bytes")
    admitted = policy.admit(
        tmp_path / "input.mp4", byte_length=11, provenance_reference="prov-1"
    )
    assert admitted == (tmp_path / "input.mp4").resolve()
    with pytest.raises(VideoSkillError, match="escapes"):
        policy.admit(
            tmp_path.parent / "outside.mp4",
            byte_length=100,
            provenance_reference="prov-1",
        )
    with pytest.raises(VideoSkillError, match="provenance"):
        policy.admit(tmp_path / "input.mp4", byte_length=11, provenance_reference=None)
    with pytest.raises(VideoSkillError, match="does not match"):
        policy.admit(
            tmp_path / "input.mp4", byte_length=10, provenance_reference="prov-1"
        )


def test_thumbnail_request_is_content_addressed_and_bounded() -> None:
    request = ThumbnailRequest("thumb-1", ARTIFACT, 500, 1280, 720, "ILAIOS")
    assert request.width == 1280
    with pytest.raises(VideoSkillError, match="safety bound"):
        ThumbnailRequest("thumb-2", ARTIFACT, 0, 1280, 720, "x" * 121)
