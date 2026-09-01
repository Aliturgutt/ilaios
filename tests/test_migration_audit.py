import csv
from pathlib import Path

from tools.migration_audit import (
    CANONICAL_NAME,
    implementation_proof_for,
    iter_completion_requirements,
    iter_requirements,
    status_for,
)


def test_requirement_extraction_preserves_normative_lines(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "## 3.1 Control\n### Quality Gates\nThe system shall deny.\n- negative test\n",
        encoding="utf-8",
    )
    requirements = iter_requirements(source)
    assert [item[3] for item in requirements] == [
        "The system shall deny.",
        "- negative test",
    ]


def test_internal_authoring_comment_is_not_a_product_requirement(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "The system shall deny.\n<!--\nThe draft must expand.\n-->\n", encoding="utf-8"
    )
    assert [item[3] for item in iter_requirements(source)] == ["The system shall deny."]


def test_status_never_claims_implementation_without_evidence() -> None:
    assert status_for("3.1", (), True) == "MISSING_IMPLEMENTATION"
    assert status_for("3.1", ("tests/control.py",), True) == "PARTIAL"
    assert status_for("3.1", (), False) == "MISSING_DOCUMENTATION"
    assert status_for("8.9", ("proof",), True, exact_proof=True) == "IMPLEMENTED"


def test_gov_i01_exact_proof_requires_code_test_and_durable_evidence() -> None:
    root = Path(__file__).parents[1]
    proof = implementation_proof_for(
        "8.9",
        "Usage controls shall support per-user, per-tenant, per-project, per-job, "
        "per-provider, and per-model scopes.",
        root,
    )
    assert proof == (
        "services/ai_governance.py",
        "tests/test_ai_governance.py",
        "evidence/migration/ILATEN_TO_ILAIOS/GOV.I01.md",
    )


def test_completion_requirements_include_only_sections_eight_and_nine() -> None:
    root = Path(__file__).parents[1]
    canonical = root / "docs/canonical" / CANONICAL_NAME
    requirements = iter_completion_requirements(canonical)
    assert requirements
    assert {section.split(".")[0] for _, section, _, _ in requirements} == {"8", "9"}


def test_every_legacy_requirement_is_preserved_in_ilaios_canonical() -> None:
    root = Path(__file__).parents[1]
    matrix = root / "docs/migration/ILATEN_TO_ILAIOS_MIGRATION_MATRIX.csv"
    canonical = (root / "docs/canonical" / CANONICAL_NAME).read_text(encoding="utf-8")
    missing: list[tuple[str, str]] = []
    with matrix.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["requirement_id"].startswith("ILATEN-"):
                continue
            requirement = row["ilaten_requirement"]
            migrated = (
                requirement.replace("ILATEN", "ILAIOS")
                .replace("Ilaten", "ILAIOS")
                .replace("ilaten", "ilaios")
            )
            if migrated not in canonical:
                missing.append((row["legacy_source"], migrated))
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
    assert (
        "No RELEASE.R01, RELEASE.R02, or RELEASE.R03 promotion was performed."
        not in canonical
    )
