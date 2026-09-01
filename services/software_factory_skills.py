"""First-party governed skill registry and execution boundary for ILAIOS SF-7."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from services.software_factory import SoftwareFactoryError

REQUIRED_SKILL_IDS = (
    "sf-requirements-analysis", "sf-repository-intelligence", "sf-change-impact-analysis",
    "sf-architecture-planning", "sf-implementation-planning", "sf-core-engineering",
    "sf-backend-engineering", "sf-frontend-engineering", "sf-windows-desktop", "sf-integration-engineering",
    "sf-database-migration", "sf-api-contract", "sf-test-design", "sf-test-generation",
    "sf-debug-repair", "sf-refactor", "sf-migration", "sf-code-review", "sf-security-review",
    "sf-dependency-governance", "sf-license-provenance", "sf-build", "sf-release-readiness",
    "sf-runtime-qa", "sf-recovery",
)
REQUIRED_FILES = ("SKILL.md", "PROVENANCE.md", "manifest.yaml", "input.schema.json", "output.schema.json", "evals/evals.json")
REQUIRED_EVAL_KINDS = frozenset({"GOLDEN", "NEGATIVE", "ADVERSARIAL", "MALFORMED", "REGRESSION"})
CANONICAL_DENY_SET = frozenset({"direct_master_mutation", "production_mutation", "governance_bypass", "secret_retrieval", "unrestricted_network", "third_party_code_copy", "unsupported_dependency", "self_certification"})
ALLOWED_RUNTIME_ADAPTERS = frozenset({"ilaios.runtime.python", "ilaios.runtime.node", "ilaios.runtime.flutter"})
ALLOWED_TOOLS = frozenset({"repository_intelligence", "runtime_adapter", "governance", "evidence_chain"})
ALLOWED_RISK_CLASSES = frozenset({"low", "medium", "high", "critical"})
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class RepositoryIntelligencePort(Protocol):
    def inspect(self, repository: Path, base_sha: str) -> Mapping[str, object]: ...


class RuntimeAdapterPort(Protocol):
    def validate(self, adapter_id: str, repository: Path) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class SkillManifest:
    skill_id: str
    version: str
    domain: str
    owner: str
    maturity: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    required_capabilities: frozenset[str]
    required_policy: str
    allowed_runtime_adapters: frozenset[str]
    allowed_tools: frozenset[str]
    forbidden_actions: frozenset[str]
    emitted_evidence: frozenset[str]
    risk_class: str
    independent_review_required: bool


@dataclass(frozen=True, slots=True)
class SkillPackage:
    root: Path
    manifest: SkillManifest
    input_schema: Mapping[str, object]
    output_schema: Mapping[str, object]
    evals: tuple[Mapping[str, object], ...]


@dataclass(frozen=True, slots=True)
class SkillExecutionRequest:
    skill_id: str
    repository: Path
    base_sha: str
    actor_id: str
    tenant_id: str
    policy_allowed: bool
    payload: Mapping[str, object]
    requested_capabilities: frozenset[str] = frozenset()
    requested_actions: frozenset[str] = frozenset()
    runtime_adapter: str | None = None


@dataclass(frozen=True, slots=True)
class SkillExecutionResult:
    skill_id: str
    version: str
    status: str
    repository_evidence: Mapping[str, object]
    runtime_evidence: Mapping[str, object] | None
    emitted_evidence: tuple[str, ...]
    independent_review_required: bool


class SkillRegistry:
    """Fail closed unless the complete 25-skill first-party family is valid."""
    def __init__(self, skills_root: Path) -> None:
        self._root = skills_root.resolve()
        self._packages = self._load_all()

    @property
    def skill_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._packages))

    def resolve(self, skill_id: str) -> SkillPackage:
        package = self._packages.get(skill_id)
        if package is None:
            raise SoftwareFactoryError(f"unknown software-factory skill: {skill_id}")
        return package

    def _load_all(self) -> dict[str, SkillPackage]:
        if not self._root.is_dir():
            raise SoftwareFactoryError("SF-7 skill root is unavailable")
        discovered = {path.name for path in self._root.iterdir() if path.is_dir() and not path.name.startswith(".")}
        required = set(REQUIRED_SKILL_IDS)
        if discovered != required:
            raise SoftwareFactoryError(f"SF-7 skill registry mismatch: missing={sorted(required-discovered)}, extra={sorted(discovered-required)}")
        packages: dict[str, SkillPackage] = {}
        identities: set[tuple[str, str]] = set()
        for skill_id in REQUIRED_SKILL_IDS:
            package = self._load_package(self._root / skill_id)
            identity = (package.manifest.skill_id, package.manifest.version)
            if package.manifest.skill_id in packages or identity in identities:
                raise SoftwareFactoryError("duplicate SF-7 skill identity")
            identities.add(identity)
            packages[package.manifest.skill_id] = package
        return packages

    def _load_package(self, root: Path) -> SkillPackage:
        for relative in REQUIRED_FILES:
            if not (root / relative).is_file():
                raise SoftwareFactoryError(f"incomplete SF-7 package {root.name}: {relative}")
        tests_dir = root / "tests"
        if not tests_dir.is_dir() or not any(tests_dir.glob("test_*.py")):
            raise SoftwareFactoryError(f"incomplete SF-7 package {root.name}: tests")
        provenance = (root / "PROVENANCE.md").read_text(encoding="utf-8")
        for marker in ("FIRST-PARTY ILAIOS IMPLEMENTATION", "INDEPENDENTLY AUTHORED", "CODE/TEXT IMPORTED = NONE", "COMMERCIAL COMPATIBILITY = ACCEPTABLE"):
            if marker not in provenance:
                raise SoftwareFactoryError(f"invalid SF-7 provenance: {root.name}")
        manifest = _manifest(_load_json(root / "manifest.yaml"))
        if manifest.skill_id != root.name:
            raise SoftwareFactoryError("manifest skill_id must match package directory")
        input_schema = _schema(_load_json(root / "input.schema.json"))
        output_schema = _schema(_load_json(root / "output.schema.json"))
        eval_doc = _load_json(root / "evals/evals.json")
        raw_cases = eval_doc.get("cases")
        if not isinstance(raw_cases, list):
            raise SoftwareFactoryError("SF-7 eval cases must be a list")
        evals = tuple(_mapping(item, "eval case") for item in raw_cases)
        kinds = {cast(str, case.get("kind")) for case in evals if isinstance(case.get("kind"), str)}
        if kinds != REQUIRED_EVAL_KINDS:
            raise SoftwareFactoryError(f"incomplete SF-7 eval matrix: {root.name}")
        return SkillPackage(root, manifest, input_schema, output_schema, evals)


class SkillExecutor:
    """Validate and dispatch SF-7 work through canonical SF-5/SF-6 ports."""
    def __init__(self, registry: SkillRegistry, repository_intelligence: RepositoryIntelligencePort, runtime: RuntimeAdapterPort) -> None:
        self._registry = registry
        self._repository_intelligence = repository_intelligence
        self._runtime = runtime

    def execute(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        package = self._registry.resolve(request.skill_id)
        _validate_request(request, package.manifest)
        _validate_instance(request.payload, package.input_schema, "$")
        repository_evidence = self._repository_intelligence.inspect(request.repository.resolve(), request.base_sha)
        runtime_evidence: Mapping[str, object] | None = None
        if request.runtime_adapter is not None:
            runtime_evidence = self._runtime.validate(request.runtime_adapter, request.repository.resolve())
        return SkillExecutionResult(package.manifest.skill_id, package.manifest.version, "READY", repository_evidence, runtime_evidence, tuple(sorted(package.manifest.emitted_evidence)), package.manifest.independent_review_required)

    def validate_output(self, skill_id: str, output: Mapping[str, object]) -> None:
        package = self._registry.resolve(skill_id)
        _validate_instance(output, package.output_schema, "$")
        if output.get("skill_id") != package.manifest.skill_id or output.get("version") != package.manifest.version:
            raise SoftwareFactoryError("SF-7 output identity mismatch")
        if package.manifest.independent_review_required and output.get("review_required") is not True:
            raise SoftwareFactoryError("SF-7 independent review requirement cannot be removed")


def default_skills_root(repository_root: Path) -> Path:
    return repository_root.resolve() / "tools" / "software-factory" / "skills"


def _validate_request(request: SkillExecutionRequest, manifest: SkillManifest) -> None:
    if not request.actor_id.strip() or not request.tenant_id.strip():
        raise SoftwareFactoryError("SF-7 requires resolved actor and tenant")
    if _SHA1.fullmatch(request.base_sha) is None:
        raise SoftwareFactoryError("SF-7 requires a lowercase repository base SHA")
    if not request.repository.is_absolute():
        raise SoftwareFactoryError("SF-7 repository path must be absolute")
    if not request.policy_allowed:
        raise SoftwareFactoryError("SF-7 policy denied execution")
    if not request.requested_capabilities.issubset(manifest.required_capabilities):
        raise SoftwareFactoryError("SF-7 requested capability exceeds manifest")
    if request.requested_actions & CANONICAL_DENY_SET:
        raise SoftwareFactoryError("SF-7 canonical deny-set blocked requested action")
    if manifest.forbidden_actions != frozenset({"sf7.default-deny"}):
        raise SoftwareFactoryError("SF-7 manifest is not bound to canonical deny-set")
    if not manifest.allowed_tools.issubset(ALLOWED_TOOLS):
        raise SoftwareFactoryError("SF-7 manifest requests unknown tool")
    if request.runtime_adapter is not None and (request.runtime_adapter not in ALLOWED_RUNTIME_ADAPTERS or request.runtime_adapter not in manifest.allowed_runtime_adapters):
        raise SoftwareFactoryError("SF-7 runtime adapter is not allowed")


def _manifest(document: Mapping[str, object]) -> SkillManifest:
    def text(name: str) -> str:
        value = document.get(name)
        if not isinstance(value, str) or not value.strip():
            raise SoftwareFactoryError(f"manifest {name} must be non-empty")
        return value
    def strings(name: str) -> frozenset[str]:
        value = document.get(name)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SoftwareFactoryError(f"manifest {name} must be a string list")
        return frozenset(cast(list[str], value))
    review = document.get("independent_review_required")
    if not isinstance(review, bool):
        raise SoftwareFactoryError("manifest independent_review_required must be boolean")
    risk = text("risk_class")
    if risk not in ALLOWED_RISK_CLASSES:
        raise SoftwareFactoryError("manifest risk_class is invalid")
    adapters = strings("allowed_runtime_adapters")
    if not adapters.issubset(ALLOWED_RUNTIME_ADAPTERS):
        raise SoftwareFactoryError("manifest runtime adapter is unknown")
    forbidden = strings("forbidden_actions")
    if forbidden != frozenset({"sf7.default-deny"}):
        raise SoftwareFactoryError("manifest must use canonical SF-7 deny-set")
    return SkillManifest(text("skill_id"), text("version"), text("domain"), text("owner"), text("maturity"), tuple(sorted(strings("inputs"))), tuple(sorted(strings("outputs"))), strings("required_capabilities"), text("required_policy"), adapters, strings("allowed_tools"), forbidden, strings("emitted_evidence"), risk, review)


def _load_json(path: Path) -> Mapping[str, object]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), "document")
    except (OSError, json.JSONDecodeError) as error:
        raise SoftwareFactoryError(f"invalid SF-7 machine-readable document: {path}") from error


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise SoftwareFactoryError(f"SF-7 {label} must be an object")
    return cast(dict[str, object], value)


def _schema(document: Mapping[str, object]) -> Mapping[str, object]:
    properties = document.get("properties")
    required = document.get("required")
    if document.get("type") != "object" or not isinstance(properties, dict) or not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise SoftwareFactoryError("SF-7 schema must define object properties and required fields")
    if not set(cast(list[str], required)).issubset(properties):
        raise SoftwareFactoryError("SF-7 schema required fields must exist in properties")
    return document


def _validate_instance(value: object, schema: Mapping[str, object], path: str) -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, Mapping):
            raise SoftwareFactoryError(f"{path} must be an object")
        properties = _mapping(schema.get("properties"), "schema properties")
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise SoftwareFactoryError("invalid schema required declaration")
        for key in cast(list[str], required):
            if key not in value:
                raise SoftwareFactoryError(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                raise SoftwareFactoryError(f"{path} has unknown fields")
        for key, item in value.items():
            child = properties.get(key)
            if child is not None:
                _validate_instance(item, _mapping(child, "schema property"), f"{path}.{key}")
        return
    if expected == "array":
        if not isinstance(value, list):
            raise SoftwareFactoryError(f"{path} must be an array")
        child = schema.get("items")
        if child is not None:
            mapped = _mapping(child, "array item schema")
            for index, item in enumerate(value):
                _validate_instance(item, mapped, f"{path}[{index}]")
        return
    if expected == "string":
        if not isinstance(value, str):
            raise SoftwareFactoryError(f"{path} must be a string")
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            raise SoftwareFactoryError(f"{path} is too short")
    elif expected == "boolean" and not isinstance(value, bool):
        raise SoftwareFactoryError(f"{path} must be boolean")
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise SoftwareFactoryError(f"{path} is outside schema enum")
