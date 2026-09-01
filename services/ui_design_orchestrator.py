"""Governed orchestration bridge from UI intent to the Software Factory coding skill.

The bridge never executes generated code. It resolves a deterministic UI spec,
then submits that spec as structured data to the existing SF-7
``sf-frontend-engineering`` admission boundary. Repository mutation remains
inside the governed Software Factory and direct master/production mutation stays
forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.software_factory import SoftwareFactoryError
from services.software_factory_skills import (
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutor,
)
from src.ilaios_ui_design import UIDesignSpec, resolve_ui_design

FRONTEND_CODING_SKILL_ID = "sf-frontend-engineering"


@dataclass(frozen=True, slots=True)
class UIDesignCodingRequest:
    prompt: str
    repository: Path
    base_sha: str
    actor_id: str
    tenant_id: str
    changed_paths: tuple[str, ...]
    policy_allowed: bool
    product: str | None = None
    runtime_adapter: str | None = None


@dataclass(frozen=True, slots=True)
class UIDesignCodingResult:
    ui_spec: UIDesignSpec
    coding_skill: SkillExecutionResult


class UIDesignOrchestrator:
    """Route UI work into the canonical governed frontend coding skill."""

    def __init__(self, coding_executor: SkillExecutor) -> None:
        self._coding_executor = coding_executor

    def execute(self, request: UIDesignCodingRequest) -> UIDesignCodingResult:
        _validate_request(request)
        spec = resolve_ui_design(request.prompt, product=request.product)
        payload: dict[str, object] = {
            "intent": request.prompt.strip(),
            "changed_paths": list(request.changed_paths),
            "ui_spec": spec.to_dict(),
        }
        coding_request = SkillExecutionRequest(
            skill_id=FRONTEND_CODING_SKILL_ID,
            repository=request.repository.resolve(),
            base_sha=request.base_sha,
            actor_id=request.actor_id.strip(),
            tenant_id=request.tenant_id.strip(),
            policy_allowed=request.policy_allowed,
            payload=payload,
            requested_capabilities=frozenset({"repository_intelligence", "governance"}),
            requested_actions=frozenset(),
            runtime_adapter=request.runtime_adapter,
        )
        result = self._coding_executor.execute(coding_request)
        if result.skill_id != FRONTEND_CODING_SKILL_ID or result.status != "READY":
            raise SoftwareFactoryError("frontend coding skill did not reach governed READY state")
        return UIDesignCodingResult(spec, result)


def _validate_request(request: UIDesignCodingRequest) -> None:
    if not request.repository.is_absolute():
        raise SoftwareFactoryError("UI orchestration requires an absolute repository path")
    if not request.changed_paths:
        raise SoftwareFactoryError("UI orchestration requires bounded changed_paths")
    for path in request.changed_paths:
        if not path or path != path.strip() or path.startswith("/") or ".." in path.split("/"):
            raise SoftwareFactoryError("UI orchestration changed_paths must be bounded relative paths")
    if not request.actor_id.strip() or not request.tenant_id.strip():
        raise SoftwareFactoryError("UI orchestration requires resolved actor and tenant")
    if not request.policy_allowed:
        raise SoftwareFactoryError("UI orchestration policy denied execution")
