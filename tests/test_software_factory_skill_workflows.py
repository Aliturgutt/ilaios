"""Representative SF-7 workflow dispatch coverage required by the phase contract."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from services.software_factory_skills import SkillExecutionRequest, SkillExecutor, SkillRegistry, default_skills_root

ROOT = Path(__file__).resolve().parents[1]
SKILLS = default_skills_root(ROOT)
BASE_SHA = "b" * 40

class _Repo:
    def inspect(self, repository: Path, base_sha: str) -> Mapping[str, object]:
        return {"repository": str(repository), "base_sha": base_sha}

class _Runtime:
    def validate(self, adapter_id: str, repository: Path) -> Mapping[str, object]:
        return {"adapter_id": adapter_id, "passed": True, "repository": str(repository)}

WORKFLOWS: tuple[tuple[str, dict[str, object], str | None], ...] = (
    ("sf-backend-engineering", {"intent":"backend feature","changed_paths":["services/x.py"]}, "ilaios.runtime.python"),
    ("sf-frontend-engineering", {"intent":"frontend feature","changed_paths":["apps/website/x.tsx"]}, "ilaios.runtime.node"),
    ("sf-integration-engineering", {"intent":"cross-stack integration","changed_paths":["services/x.py","apps/website/x.tsx"]}, "ilaios.runtime.python"),
    ("sf-debug-repair", {"intent":"bug repair","failure_evidence":["failing-test"],"changed_paths":["services/x.py"]}, "ilaios.runtime.python"),
    ("sf-refactor", {"intent":"refactor","changed_paths":["services/x.py"]}, "ilaios.runtime.python"),
    ("sf-api-contract", {"intent":"api change","contract_changes":["GET /v1/x"]}, "ilaios.runtime.python"),
    ("sf-database-migration", {"intent":"db migration","schema_changes":["add nullable column"]}, "ilaios.runtime.python"),
    ("sf-dependency-governance", {"intent":"dependency addition","dependency_changes":["example==1"]}, "ilaios.runtime.python"),
    ("sf-release-readiness", {"intent":"release readiness","artifact_references":["artifact-1"],"validation_evidence":["tests-pass"]}, "ilaios.runtime.python"),
)

def test_representative_workflows_dispatch_through_governed_layer(tmp_path: Path) -> None:
    registry = SkillRegistry(SKILLS)
    executor = SkillExecutor(registry, _Repo(), _Runtime())
    for skill_id, payload, runtime_adapter in WORKFLOWS:
        package = registry.resolve(skill_id)
        requested = set(package.manifest.required_capabilities)
        result = executor.execute(SkillExecutionRequest(skill_id=skill_id, repository=tmp_path.resolve(), base_sha=BASE_SHA, actor_id="workflow-agent", tenant_id="tenant", policy_allowed=True, payload=payload, requested_capabilities=frozenset(requested), runtime_adapter=runtime_adapter))
        assert result.status == "READY"
        assert result.skill_id == skill_id
