from pathlib import Path

from services.agent_registry import registration_for
from services.research_factory_skills import (
    RESEARCH_FACTORY_SKILLS,
    RESEARCH_FACTORY_SKILL_IDS,
    default_research_skills_root,
    validate_research_factory_skills,
)
from services.skill_taxonomy import resolve_logical_skill


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_research_skill_family_is_complete_and_package_backed() -> None:
    root = default_research_skills_root(_repository_root())
    validate_research_factory_skills(root)
    assert RESEARCH_FACTORY_SKILL_IDS == (
        "ilaios-research-planning",
        "ilaios-research",
        "ilaios-source-validation",
        "ilaios-contradiction-check",
        "ilaios-citation-validation",
        "ilaios-research-synthesis",
    )
    assert all((root / skill_id / "SKILL.md").is_file() for skill_id in RESEARCH_FACTORY_SKILL_IDS)


def test_research_bindings_never_widen_canonical_intelligence_authority() -> None:
    for binding in RESEARCH_FACTORY_SKILLS:
        manifest = registration_for(binding.owner_agent_id).manifest
        assert manifest.team == "intelligence"
        assert binding.capability in manifest.capabilities
        assert binding.permission in manifest.permissions
        assert resolve_logical_skill(binding.logical_id).backing_skill_ids == (
            binding.skill_id,
        )


def test_research_packages_do_not_claim_source_acquisition_authority() -> None:
    root = default_research_skills_root(_repository_root())
    for skill_id in RESEARCH_FACTORY_SKILL_IDS:
        text = (root / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert "No direct network authority" in text
        assert "Status: IMPLEMENTED" in text
        assert "Owner: ILAIOS" in text
