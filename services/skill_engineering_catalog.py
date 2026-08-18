"""Fail-closed catalog for ILAIOS skill-engineering packages."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from services.skill_taxonomy import resolve_logical_skill

_REQUIRED_FILES = (
    "SKILL.md",
    "PROVENANCE.md",
    "manifest.yaml",
    "input.schema.json",
    "output.schema.json",
    "evals/evals.json",
)
_REQUIRED_PROVENANCE_MARKERS = (
    "FIRST-PARTY ILAIOS IMPLEMENTATION",
    "INDEPENDENTLY AUTHORED",
    "CODE/TEXT IMPORTED = NONE",
)
_ALLOWED_TOOLS = frozenset(
    {"repository_intelligence", "governance", "evidence_chain"}
)
_ALLOWED_CAPABILITIES = frozenset(
    {"repository_intelligence", "governance", "evidence_chain"}
)
_REQUIRED_POLICY = "ilaios.skill-engineering.governed"
_ALLOWED_RISK_CLASSES = frozenset({"low", "medium", "high", "critical"})
_ALLOWED_SOURCE_MATURITY = frozenset({"DESIGNED", "SPECIFIED", "IMPLEMENTED"})
_REQUIRED_DOMAIN = "skill-engineering"
_REQUIRED_EVAL_KINDS = frozenset(
    {"GOLDEN", "NEGATIVE", "ADVERSARIAL", "MALFORMED", "REGRESSION"}
)
_REQUIRED_EMITTED_EVIDENCE = frozenset(
    {
        "skill_identity",
        "logical_id",
        "provenance",
        "validation_plan",
        "unresolved_blockers",
    }
)
_REQUIRED_FORBIDDEN_ACTIONS = frozenset(
    {
        "direct_master_mutation",
        "production_mutation",
        "governance_bypass",
        "secret_retrieval",
        "unrestricted_network",
        "third_party_code_copy",
        "self_certification",
    }
)


@dataclass(frozen=True, slots=True)
class SkillEngineeringPackage:
    root: Path
    skill_id: str
    logical_id: str
    version: str
    maturity: str
    required_capabilities: frozenset[str]
    allowed_tools: frozenset[str]
    forbidden_actions: frozenset[str]
    independent_review_required: bool
    eval_kinds: frozenset[str]


class SkillEngineeringCatalog:
    """Load first-party skill-engineering packages without granting execution."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._packages = self._load_all()

    @property
    def skill_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._packages))

    def resolve(self, skill_id: str) -> SkillEngineeringPackage:
        package = self._packages.get(skill_id)
        if package is None:
            raise ValueError(f"unknown ILAIOS skill-engineering package: {skill_id}")
        return package

    def _load_all(self) -> dict[str, SkillEngineeringPackage]:
        if not self._root.is_dir():
            raise ValueError("ILAIOS skill-engineering root is unavailable")
        packages: dict[str, SkillEngineeringPackage] = {}
        for package_root in sorted(self._root.iterdir()):
            if not package_root.is_dir() or package_root.name.startswith("."):
                continue
            package = self._load_package(package_root)
            if package.skill_id in packages:
                raise ValueError("duplicate ILAIOS skill-engineering skill_id")
            packages[package.skill_id] = package
        if "skill-create" not in packages:
            raise ValueError("ILAIOS skill-engineering requires skill-create")
        return packages

    def _load_package(self, root: Path) -> SkillEngineeringPackage:
        for relative in _REQUIRED_FILES:
            if not (root / relative).is_file():
                raise ValueError(
                    f"incomplete ILAIOS skill-engineering package {root.name}: "
                    f"{relative}"
                )

        provenance = (root / "PROVENANCE.md").read_text(encoding="utf-8")
        for marker in _REQUIRED_PROVENANCE_MARKERS:
            if marker not in provenance:
                raise ValueError(
                    f"invalid ILAIOS skill-engineering provenance: {root.name}"
                )

        manifest = _load_json(root / "manifest.yaml")
        skill_id = _required_text(manifest, "skill_id")
        logical_id = _required_text(manifest, "logical_id")
        version = _required_text(manifest, "version")
        maturity = _required_text(manifest, "maturity")
        if skill_id != root.name:
            raise ValueError("skill-engineering manifest skill_id must match directory")

        logical_node = resolve_logical_skill(logical_id)
        if logical_node.layer != "skill-engineering":
            raise ValueError(
                "skill-engineering package logical_id must stay in skill-engineering"
            )
        if skill_id != f"skill-{logical_node.path[-1]}":
            raise ValueError(
                "skill-engineering skill_id must match its logical taxonomy leaf"
            )

        domain = _required_text(manifest, "domain")
        if domain != _REQUIRED_DOMAIN:
            raise ValueError("skill-engineering package domain is invalid")

        required_policy = _required_text(manifest, "required_policy")
        if required_policy != _REQUIRED_POLICY:
            raise ValueError("skill-engineering package requires canonical policy")

        required_capabilities = _string_set(manifest, "required_capabilities")
        if not required_capabilities.issubset(_ALLOWED_CAPABILITIES):
            raise ValueError("skill-engineering package requests unknown capability")

        allowed_tools = _string_set(manifest, "allowed_tools")
        if not allowed_tools.issubset(_ALLOWED_TOOLS):
            raise ValueError("skill-engineering package requests unknown tool")

        forbidden_actions = _string_set(manifest, "forbidden_actions")
        if forbidden_actions != _REQUIRED_FORBIDDEN_ACTIONS:
            raise ValueError("skill-engineering package must preserve canonical deny-set")

        risk_class = _required_text(manifest, "risk_class")
        if risk_class not in _ALLOWED_RISK_CLASSES:
            raise ValueError("skill-engineering package risk_class is invalid")
        if maturity not in _ALLOWED_SOURCE_MATURITY:
            raise ValueError(
                "skill-engineering source maturity cannot claim tested or verified"
            )

        emitted_evidence = _string_set(manifest, "emitted_evidence")
        if not _REQUIRED_EMITTED_EVIDENCE.issubset(emitted_evidence):
            raise ValueError("skill-engineering evidence declaration is incomplete")

        independent_review_required = manifest.get("independent_review_required")
        if not isinstance(independent_review_required, bool):
            raise ValueError(
                "skill-engineering independent_review_required must be boolean"
            )
        if risk_class in {"high", "critical"} and not independent_review_required:
            raise ValueError(
                "high-risk skill-engineering packages require independent review"
            )

        _validate_schema(_load_json(root / "input.schema.json"))
        _validate_schema(_load_json(root / "output.schema.json"))
        eval_document = _load_json(root / "evals/evals.json")
        cases = eval_document.get("cases")
        if not isinstance(cases, list):
            raise ValueError("skill-engineering eval cases must be a list")
        eval_kinds = frozenset(
            cast(str, case.get("kind"))
            for case in cases
            if isinstance(case, dict) and isinstance(case.get("kind"), str)
        )
        if eval_kinds != _REQUIRED_EVAL_KINDS:
            raise ValueError("skill-engineering eval matrix is incomplete")

        return SkillEngineeringPackage(
            root=root,
            skill_id=skill_id,
            logical_id=logical_id,
            version=version,
            maturity=maturity,
            required_capabilities=required_capabilities,
            allowed_tools=allowed_tools,
            forbidden_actions=forbidden_actions,
            independent_review_required=independent_review_required,
            eval_kinds=eval_kinds,
        )


def default_skill_engineering_root(repository_root: Path) -> Path:
    return repository_root.resolve() / "tools" / "skill-engineering" / "skills"


def _load_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid skill-engineering document: {path}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"skill-engineering document must be an object: {path}")
    return cast(dict[str, object], value)


def _required_text(document: Mapping[str, object], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"skill-engineering manifest {field} must be non-empty")
    return value


def _string_set(document: Mapping[str, object], field: str) -> frozenset[str]:
    value = document.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"skill-engineering manifest {field} must be a string list")
    return frozenset(cast(list[str], value))


def _validate_schema(document: Mapping[str, object]) -> None:
    properties = document.get("properties")
    required = document.get("required")
    if (
        document.get("type") != "object"
        or not isinstance(properties, dict)
        or not isinstance(required, list)
        or not all(isinstance(item, str) for item in required)
    ):
        raise ValueError("skill-engineering schema must define object properties")
    if not set(cast(list[str], required)).issubset(properties):
        raise ValueError("skill-engineering schema required fields must exist")
