"""First-party security methodology skill packages for the canonical ILAIOS runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import registration_for
from services.named_agent_executor import NamedAgentExecutor


class SecurityMethodologySkillError(ValueError):
    """A security methodology skill package violated its governed contract."""


@dataclass(frozen=True, slots=True)
class SecurityMethodologySkill:
    skill_id: str
    owner_agent_id: str
    capability: str


SECURITY_REVIEW_SKILL_ID = "ilaios-security-review"
DIFFERENTIAL_REVIEW_SKILL_ID = "ilaios-differential-review"
AGENTIC_ACTION_AUDIT_SKILL_ID = "ilaios-agentic-action-audit"
THREAT_MODEL_SKILL_ID = "ilaios-threat-model"
SUPPLY_CHAIN_AUDIT_SKILL_ID = "ilaios-supply-chain-audit"

SECURITY_METHODOLOGY_SKILLS: tuple[SecurityMethodologySkill, ...] = (
    SecurityMethodologySkill(
        SECURITY_REVIEW_SKILL_ID,
        "ilaios.agent.security.codesec.v1",
        "security.sast",
    ),
    SecurityMethodologySkill(
        DIFFERENTIAL_REVIEW_SKILL_ID,
        "ilaios.agent.security.codesec.v1",
        "security.sast",
    ),
    SecurityMethodologySkill(
        AGENTIC_ACTION_AUDIT_SKILL_ID,
        "ilaios.agent.security.infrastructure.v1",
        "security.infrastructure",
    ),
    SecurityMethodologySkill(
        THREAT_MODEL_SKILL_ID,
        "ilaios.agent.security.codesec.v1",
        "security.sast",
    ),
    SecurityMethodologySkill(
        SUPPLY_CHAIN_AUDIT_SKILL_ID,
        "ilaios.agent.security.supply-chain.v1",
        "security.dependency",
    ),
)

_SKILLS_BY_ID = {item.skill_id: item for item in SECURITY_METHODOLOGY_SKILLS}
_REQUIRED_PROVENANCE_MARKERS = (
    "FIRST-PARTY ILAIOS IMPLEMENTATION",
    "INDEPENDENTLY AUTHORED",
    "CODE/TEXT IMPORTED = NONE",
    "COMMERCIAL COMPATIBILITY = ACCEPTABLE",
)


def default_security_methodology_skills_root(repository_root: Path) -> Path:
    return repository_root.resolve() / "tools" / "security-factory" / "skills"


def definition_for(skill_id: str) -> SecurityMethodologySkill | None:
    return _SKILLS_BY_ID.get(skill_id)


def ensure_security_methodology_skills(
    executor: NamedAgentExecutor,
    skills_root: Path,
) -> dict[str, str]:
    root = skills_root.resolve()
    _validate_root(root)
    digests: dict[str, str] = {}
    for definition in SECURITY_METHODOLOGY_SKILLS:
        registration = registration_for(definition.owner_agent_id)
        if definition.capability not in registration.manifest.capabilities:
            raise SecurityMethodologySkillError(
                f"skill capability exceeds owner manifest: {definition.skill_id}"
            )
        package = root / definition.skill_id
        skill_content = (package / "SKILL.md").read_bytes()
        digests[definition.skill_id] = executor.ensure_skill(
            definition.skill_id,
            skill_content,
            frozenset({definition.capability}),
        )
    return digests


def _validate_root(root: Path) -> None:
    if not root.is_dir():
        raise SecurityMethodologySkillError(
            "security methodology skill registry is unavailable"
        )
    contract = root / "CONTRACT.md"
    if not contract.is_file():
        raise SecurityMethodologySkillError(
            "security methodology common contract is missing"
        )
    discovered = {
        item.name
        for item in root.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    }
    expected = set(_SKILLS_BY_ID)
    if discovered != expected:
        raise SecurityMethodologySkillError(
            "security methodology registry mismatch "
            f"missing={sorted(expected - discovered)} "
            f"extra={sorted(discovered - expected)}"
        )
    for definition in SECURITY_METHODOLOGY_SKILLS:
        package = root / definition.skill_id
        skill_path = package / "SKILL.md"
        provenance_path = package / "PROVENANCE.md"
        if not skill_path.is_file() or not provenance_path.is_file():
            raise SecurityMethodologySkillError(
                f"incomplete security methodology package: {definition.skill_id}"
            )
        skill_text = skill_path.read_text(encoding="utf-8")
        if f"name: {definition.skill_id}" not in skill_text.splitlines()[:8]:
            raise SecurityMethodologySkillError(
                f"skill identity mismatch: {definition.skill_id}"
            )
        if not skill_text.strip():
            raise SecurityMethodologySkillError(
                f"empty security methodology skill: {definition.skill_id}"
            )
        provenance = provenance_path.read_text(encoding="utf-8")
        for marker in _REQUIRED_PROVENANCE_MARKERS:
            if marker not in provenance:
                raise SecurityMethodologySkillError(
                    f"invalid security methodology provenance: {definition.skill_id}"
                )
