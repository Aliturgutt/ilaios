"""Repository-backed skill-engineering catalog proofs."""
from pathlib import Path

from services.skill_catalog import SKILL_ENGINEERING_CATALOG, validate_skill_engineering_catalog


def test_skill_engineering_catalog_is_complete_and_repository_backed() -> None:
    root = Path(__file__).resolve().parents[1]
    validate_skill_engineering_catalog(root)
    assert {item.package_name for item in SKILL_ENGINEERING_CATALOG} == {
        "ilaios-skill-create",
        "ilaios-skill-validate",
        "ilaios-skill-evaluate",
        "ilaios-skill-benchmark",
        "ilaios-skill-regression",
    }
