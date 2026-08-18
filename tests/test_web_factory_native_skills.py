from pathlib import Path

from services.web_factory_skills import (
    WEB_FACTORY_NATIVE_SKILL_IDS,
    WEB_FACTORY_NATIVE_SKILLS,
    validate_web_factory_native_skills,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_web_factory_native_skill_registry_is_ordered_and_unique() -> None:
    validate_web_factory_native_skills()
    assert WEB_FACTORY_NATIVE_SKILL_IDS == (
        "ilaios-web-architecture",
        "ilaios-web-design",
        "ilaios-web-accessibility",
        "ilaios-web-performance",
        "ilaios-web-validation",
        "ilaios-web-production-qa",
    )
    assert len({item.capability for item in WEB_FACTORY_NATIVE_SKILLS}) == 6


def test_web_factory_native_skill_packages_exist_and_are_first_party() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    provenance = (root / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "CODE/TEXT IMPORTED = NONE" in provenance
    assert "PROMPT/SKILL TEXT IMPORTED = NONE" in provenance
    assert "REFERENCE IMPLEMENTATION IMPORTED = NONE" in provenance
    assert "RUNTIME DEPENDENCY ON THIRD-PARTY SKILL REPOSITORIES = NONE" in provenance
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        skill = root / skill_id / "SKILL.md"
        assert skill.is_file(), skill_id
        text = skill.read_text(encoding="utf-8")
        assert f"name: {skill_id}" in text
        assert "Owner: ILAIOS" in text
        assert "Status: IMPLEMENTED" in text


def test_web_factory_native_skill_contract_is_provider_independent() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    forbidden_identity_markers = (
        "vercel-labs/agent-skills",
        "react-best-practices",
        "web-design-guidelines",
        "composition-patterns",
        "vercel-optimize",
        "claude skill",
        "codex skill",
    )
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        text = (root / skill_id / "SKILL.md").read_text(encoding="utf-8").casefold()
        assert "provider-independent" in text or "provider/framework" in text or "hosting-specific" in text
        assert all(marker not in text for marker in forbidden_identity_markers)


def test_web_factory_native_skills_do_not_import_external_skill_assets() -> None:
    root = _repo_root() / "tools" / "web-factory" / "skills"
    allowed_top_level = {"PROVENANCE.md", *WEB_FACTORY_NATIVE_SKILL_IDS}
    assert {path.name for path in root.iterdir()} == allowed_top_level
    for skill_id in WEB_FACTORY_NATIVE_SKILL_IDS:
        package = root / skill_id
        assert {path.name for path in package.iterdir()} == {"SKILL.md"}
