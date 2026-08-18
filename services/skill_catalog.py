"""Repository-backed catalog for ILAIOS skill-engineering instructions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SkillCatalogError(ValueError):
    """Repository skill package identity or structure is invalid."""


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    skill_id: str
    package_name: str


SKILL_ENGINEERING_CATALOG: tuple[SkillDefinition, ...] = (
    SkillDefinition("ilaios.skill.engineering.create.v1", "ilaios-skill-create"),
    SkillDefinition("ilaios.skill.engineering.validate.v1", "ilaios-skill-validate"),
    SkillDefinition("ilaios.skill.engineering.evaluate.v1", "ilaios-skill-evaluate"),
    SkillDefinition("ilaios.skill.engineering.benchmark.v1", "ilaios-skill-benchmark"),
    SkillDefinition("ilaios.skill.engineering.regression.v1", "ilaios-skill-regression"),
)


def validate_skill_engineering_catalog(repository_root: Path) -> None:
    ids = [item.skill_id for item in SKILL_ENGINEERING_CATALOG]
    if len(ids) != len(set(ids)) or any(not item.startswith("ilaios.skill.") for item in ids):
        raise SkillCatalogError("skill-engineering IDs must be unique canonical identities")
    for item in SKILL_ENGINEERING_CATALOG:
        root = repository_root.resolve() / "skills" / item.package_name
        for required in ("SKILL.md", "PROVENANCE.md"):
            path = root / required
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise SkillCatalogError(f"incomplete skill package: {item.package_name}/{required}")
