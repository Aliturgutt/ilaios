import importlib

from services.integrations.video_skill_governance import ALL_VIDEO_SKILLS
from services.skill_taxonomy import resolve_logical_skill
from src.video_automation.video_lifecycle_skill_manifests import VIDEO_LIFECYCLE_SKILLS
from src.video_automation.video_skills import SkillRisk, validate_video_skills


def test_video_lifecycle_skills_are_canonical_and_governed() -> None:
    validate_video_skills(VIDEO_LIFECYCLE_SKILLS)
    ids = tuple(skill.skill_id for skill in VIDEO_LIFECYCLE_SKILLS)
    assert ids == (
        "ilaios.skill.video.generation.execute",
        "ilaios.skill.video.captions.export",
        "ilaios.skill.video.composition.prepare",
        "ilaios.skill.video.render.execute",
    )
    assert set(ids).issubset({skill.skill_id for skill in ALL_VIDEO_SKILLS})


def test_video_lifecycle_skills_point_to_existing_implementations() -> None:
    for skill in VIDEO_LIFECYCLE_SKILLS:
        module_name, symbol_name = skill.implementation.split(":", 1)
        module = importlib.import_module(module_name)
        assert getattr(module, symbol_name) is not None


def test_video_lifecycle_risk_is_fail_closed_for_side_effects() -> None:
    by_id = {skill.skill_id: skill for skill in VIDEO_LIFECYCLE_SKILLS}
    generation = by_id["ilaios.skill.video.generation.execute"]
    assert generation.risk is SkillRisk.EXTERNAL_SIDE_EFFECT
    assert "provider.request" in generation.permissions
    for skill_id in (
        "ilaios.skill.video.captions.export",
        "ilaios.skill.video.composition.prepare",
        "ilaios.skill.video.render.execute",
    ):
        assert by_id[skill_id].risk is SkillRisk.MEDIA_MUTATION
        assert by_id[skill_id].permissions == ("media.read", "media.write")


def test_video_lifecycle_taxonomy_maps_one_to_one() -> None:
    expected = {
        "factories/video/generation": "ilaios.skill.video.generation.execute",
        "factories/video/captions": "ilaios.skill.video.captions.export",
        "factories/video/composition": "ilaios.skill.video.composition.prepare",
        "factories/video/render": "ilaios.skill.video.render.execute",
    }
    for logical_id, skill_id in expected.items():
        assert resolve_logical_skill(logical_id).backing_skill_ids == (skill_id,)
