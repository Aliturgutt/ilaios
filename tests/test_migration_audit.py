from pathlib import Path

from tools.migration_audit import (
    CANONICAL_NAME,
    SOURCE_NAME,
    iter_requirements,
    status_for,
)


def test_requirement_extraction_preserves_normative_lines(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("## 3.1 Control\n### Quality Gates\nThe system shall deny.\n- negative test\n", encoding="utf-8")
    requirements = iter_requirements(source)
    assert [item[3] for item in requirements] == ["The system shall deny.", "- negative test"]


def test_internal_authoring_comment_is_not_a_product_requirement(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("The system shall deny.\n<!--\nThe draft must expand.\n-->\n", encoding="utf-8")
    assert [item[3] for item in iter_requirements(source)] == ["The system shall deny."]


def test_status_never_claims_implementation_without_evidence() -> None:
    assert status_for("3.1", (), True) == "MISSING_IMPLEMENTATION"
    assert status_for("3.1", ("tests/control.py",), True) == "PARTIAL"
    assert status_for("3.1", (), False) == "MISSING_DOCUMENTATION"


def test_every_legacy_requirement_is_preserved_in_ilaios_canonical() -> None:
    root = Path(__file__).parents[1]
    source = root / "dev/openclaw/migration_input" / SOURCE_NAME
    canonical = (root / "docs/canonical" / CANONICAL_NAME).read_text(encoding="utf-8")
    missing = []
    for line, _, _, requirement in iter_requirements(source):
        migrated = requirement.replace("ILATEN", "ILAIOS").replace("Ilaten", "ILAIOS").replace("ilaten", "ilaios")
        if migrated not in canonical:
            missing.append((line, migrated))
    assert not missing, f"requirements missing from canonical: {missing[:10]}"


def test_canonical_contains_approved_governance_and_roadmap_sections() -> None:
    root = Path(__file__).parents[1]
    canonical = (root / "docs/canonical" / CANONICAL_NAME).read_text(encoding="utf-8")
    required_headings = (
        "# 8. Governance & Operations",
        "## 8.9 AI, Model, Provider, and FinOps Governance",
        "## 8.10 Data, Privacy, and Evidence Governance",
        "## 8.12 Exception, Review, and Lifecycle Governance",
        "# 9. Enterprise Roadmap & Future Evolution",
        "## 9.3 AI Capability Roadmap",
        "## 9.9 Compatibility, Migration, and Deprecation Policy",
    )
    assert all(heading in canonical for heading in required_headings)
    assert "Classification is not implementation status." in canonical
    assert "No RELEASE.R01, RELEASE.R02, or RELEASE.R03 promotion was performed." not in canonical
