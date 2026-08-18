"""Canonical catalog of repository-backed ILAIOS-native skill packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SkillCatalogError(ValueError):
    """Native skill catalog or package layout is invalid."""


@dataclass(frozen=True, slots=True)
class NativeSkillDefinition:
    skill_id: str
    package_path: str
    capability_id: str

    def __post_init__(self) -> None:
        if not self.skill_id.startswith("ilaios.skill."):
            raise SkillCatalogError("native skill IDs must use the ilaios.skill namespace")
        if not self.package_path.startswith("skills/"):
            raise SkillCatalogError("native skill packages must live under skills/")
        if not self.capability_id.startswith("ilaios.capability."):
            raise SkillCatalogError("skill capability must use canonical capability identity")


NATIVE_SKILLS: tuple[NativeSkillDefinition, ...] = (
    NativeSkillDefinition(
        "ilaios.skill.engineering.create",
        "skills/skill-engineering/create",
        "ilaios.capability.policy-governance",
    ),
    NativeSkillDefinition(
        "ilaios.skill.engineering.validate",
        "skills/skill-engineering/validate",
        "ilaios.capability.policy-governance",
    ),
    NativeSkillDefinition(
        "ilaios.skill.engineering.evaluate",
        "skills/skill-engineering/evaluate",
        "ilaios.capability.evidence-audit",
    ),
    NativeSkillDefinition(
        "ilaios.skill.engineering.benchmark",
        "skills/skill-engineering/benchmark",
        "ilaios.capability.provider-routing",
    ),
    NativeSkillDefinition(
        "ilaios.skill.engineering.regression",
        "skills/skill-engineering/regression",
        "ilaios.capability.evidence-audit",
    ),
)


def native_skill(skill_id: str) -> NativeSkillDefinition:
    for definition in NATIVE_SKILLS:
        if definition.skill_id == skill_id:
            return definition
    raise KeyError(skill_id)


def validate_skill_catalog(repo_root: Path) -> None:
    ids = [definition.skill_id for definition in NATIVE_SKILLS]
    if len(ids) != len(set(ids)):
        raise SkillCatalogError("native skill IDs must be globally unique")

    paths = [definition.package_path for definition in NATIVE_SKILLS]
    if len(paths) != len(set(paths)):
        raise SkillCatalogError("native skill package paths must be globally unique")

    root = repo_root.resolve()
    for definition in NATIVE_SKILLS:
        package = (root / definition.package_path).resolve()
        try:
            package.relative_to(root)
        except ValueError as exc:
            raise SkillCatalogError("skill package escapes repository root") from exc
        skill_file = package / "SKILL.md"
        if not skill_file.is_file():
            raise SkillCatalogError(f"missing SKILL.md for {definition.skill_id}")
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("# ilaios-skill-"):
            raise SkillCatalogError(
                f"invalid native skill heading for {definition.skill_id}"
            )
        lowered = text.casefold()
        forbidden = (
            "bypass policy engine",
            "bypass approval engine",
            "disable governance",
        )
        if any(marker in lowered for marker in forbidden):
            raise SkillCatalogError(
                f"governance bypass language in {definition.skill_id}"
            )
