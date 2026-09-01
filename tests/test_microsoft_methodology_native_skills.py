from __future__ import annotations

from pathlib import Path

from services.agent_skills_compat import load_agent_skill

ROOT = Path(__file__).resolve().parents[1]
MICROSOFT_REFERENCE_SHA = "e20084b9d230c6f3b46ce36f011e6c3e50f79f8a"

PACKAGES = {
    "ilaios-frontend-design-review": (
        "ilaios.skill.frontend.design-review.v1",
        "ILAIOS-METHODOLOGY-FRONTEND-REVIEW-V1",
    ),
    "ilaios-mcp-builder": (
        "ilaios.skill.integration.mcp-builder.v1",
        "ILAIOS-METHODOLOGY-MCP-BUILDER-V1",
    ),
    "ilaios-observability": (
        "ilaios.skill.runtime.observability.v1",
        "ILAIOS-METHODOLOGY-OBSERVABILITY-V1",
    ),
    "ilaios-governance": (
        "ilaios.skill.governance.review.v1",
        "ILAIOS-METHODOLOGY-GOVERNANCE-V1",
    ),
}

OVERLAYS = {
    "sf-implementation-planning": "skill-engineering/create",
    "sf-frontend-engineering": "ILAIOS-METHODOLOGY-FRONTEND-REVIEW-V1",
    "sf-integration-engineering": "ILAIOS-METHODOLOGY-MCP-BUILDER-V1",
    "sf-runtime-qa": "ILAIOS-METHODOLOGY-OBSERVABILITY-V1",
    "sf-code-review": "ILAIOS-METHODOLOGY-GOVERNANCE-V1",
    "sf-release-readiness": "ILAIOS-METHODOLOGY-GOVERNANCE-V1",
}


def test_methodology_packages_are_portable_without_execution_authority() -> None:
    for folder, (canonical_id, contract) in PACKAGES.items():
        package = load_agent_skill(ROOT / "skills" / folder)
        assert package.metadata.name == folder
        assert package.trust_state == "UNTRUSTED_CANDIDATE"
        assert package.execution_authorized is False
        assert package.contains_scripts is False
        assert any(
            item.relative_path == "references/acceptance-criteria.md"
            for item in package.resources
        )
        skill = (ROOT / "skills" / folder / "SKILL.md").read_text(encoding="utf-8")
        assert canonical_id in skill
        assert contract in skill


def test_methodology_skills_are_provider_neutral() -> None:
    forbidden = ("azure", "foundry", "entra", "microsoft")
    for folder in PACKAGES:
        skill = (ROOT / "skills" / folder / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in skill


def test_reference_provenance_is_clean_room_and_pinned() -> None:
    markers = (
        "FIRST-PARTY ILAIOS IMPLEMENTATION",
        "INDEPENDENTLY AUTHORED",
        "CODE/TEXT IMPORTED = NONE",
        "COMMERCIAL COMPATIBILITY = ACCEPTABLE",
    )
    for folder in PACKAGES:
        provenance = (ROOT / "skills" / folder / "PROVENANCE.md").read_text(
            encoding="utf-8"
        )
        assert MICROSOFT_REFERENCE_SHA in provenance
        for marker in markers:
            assert marker in provenance


def test_every_methodology_has_full_acceptance_matrix() -> None:
    kinds = ("GOLDEN", "NEGATIVE", "ADVERSARIAL", "MALFORMED", "REGRESSION")
    for folder in PACKAGES:
        criteria = (
            ROOT / "skills" / folder / "references" / "acceptance-criteria.md"
        ).read_text(encoding="utf-8")
        for kind in kinds:
            assert f"## {kind}" in criteria


def test_canonical_skill_create_is_single_authoring_owner() -> None:
    canonical = ROOT / "tools" / "skill-engineering" / "skills" / "skill-create"
    assert canonical.is_dir()
    assert MICROSOFT_REFERENCE_SHA in (canonical / "PROVENANCE.md").read_text(
        encoding="utf-8"
    )
    assert not (ROOT / "skills" / "ilaios-skill-engineering").exists()


def test_methodologies_are_wired_into_existing_primary_skills() -> None:
    root = ROOT / "tools" / "software-factory" / "skills"
    for primary_skill, contract in OVERLAYS.items():
        text = (root / primary_skill / "SKILL.md").read_text(encoding="utf-8")
        assert contract in text


def test_readme_documents_no_new_execution_authority() -> None:
    readme = (ROOT / "skills" / "README.md").read_text(encoding="utf-8")
    for folder in PACKAGES:
        assert folder in readme
    assert "do not create new execution identities or permissions" in readme
