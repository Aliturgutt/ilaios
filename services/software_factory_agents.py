"""SF-8 governed Engineering Agent bindings for the ILAIOS Software Factory.

This module does not create a second agent runtime, registry, policy engine, or
skill executor. It binds the canonical engineering-team identities to the SF-7
first-party skill executor behind the existing PermissionFirewall and scoped
ExecutionGrant boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from services.agent_governance import (
    AgentAdmissionEvidence,
    AgentInvocation,
    AgentSecurityError,
    PermissionFirewall,
)
from services.agent_registry import (
    CANONICAL_AGENT_REGISTRY,
    registration_for,
    registrations_for_team,
)
from services.runtime import ExecutionGrant, GrantPolicy
from services.software_factory import SoftwareFactoryError
from services.software_factory_skills import (
    REQUIRED_SKILL_IDS,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutor,
    SkillRegistry,
)


class EngineeringAgentError(SoftwareFactoryError):
    """A governed SF-8 engineering-agent invariant failed closed."""


ENGINEERING_AGENT_SKILLS: Mapping[str, tuple[str, ...]] = {
    "ilaios.agent.engineering.architect.v1": (
        "sf-requirements-analysis",
        "sf-repository-intelligence",
        "sf-change-impact-analysis",
        "sf-architecture-planning",
        "sf-implementation-planning",
    ),
    "ilaios.agent.engineering.core.v1": (
        "sf-core-engineering",
        "sf-debug-repair",
        "sf-refactor",
        "sf-migration",
    ),
    "ilaios.agent.engineering.backend.v1": (
        "sf-backend-engineering",
        "sf-database-migration",
        "sf-api-contract",
    ),
    "ilaios.agent.engineering.frontend.v1": (
        "sf-frontend-engineering",
        "sf-windows-desktop",
    ),
    "ilaios.agent.engineering.integration.v1": ("sf-integration-engineering",),
    "ilaios.agent.engineering.test.v1": (
        "sf-test-design",
        "sf-test-generation",
    ),
    "ilaios.agent.engineering.review.v1": (
        "sf-code-review",
        "sf-security-review",
        "sf-dependency-governance",
        "sf-license-provenance",
    ),
    "ilaios.agent.engineering.runtime-qa.v1": (
        "sf-build",
        "sf-runtime-qa",
    ),
    "ilaios.agent.engineering.release.v1": ("sf-release-readiness",),
    "ilaios.agent.engineering.recovery.v1": ("sf-recovery",),
}


@dataclass(frozen=True, slots=True)
class AgentSkillStep:
    """One explicitly requested SF-7 skill step within an engineering-agent task."""

    skill_id: str
    payload: Mapping[str, object]
    requested_capabilities: frozenset[str] = frozenset()
    requested_actions: frozenset[str] = frozenset()
    runtime_adapter: str | None = None


@dataclass(frozen=True, slots=True)
class EngineeringAgentTask:
    """Governed task envelope for a canonical engineering agent."""

    invocation: AgentInvocation
    grant: ExecutionGrant
    repository: Path
    base_sha: str
    tenant_id: str
    policy_allowed: bool
    steps: tuple[AgentSkillStep, ...]


@dataclass(frozen=True, slots=True)
class EngineeringAgentExecution:
    """Admission plus immutable SF-7 evidence for one engineering-agent run."""

    admission: AgentAdmissionEvidence
    skill_results: tuple[SkillExecutionResult, ...]
    status: str
    evidence_digest: str

    @property
    def verifier_id(self) -> str:
        return self.admission.verifier_id


class EngineeringAgentExecutor:
    """Execute canonical engineering identities only through governed SF-7 skills."""

    def __init__(
        self,
        registry: SkillRegistry,
        skill_executor: SkillExecutor,
        grants: GrantPolicy,
    ) -> None:
        _validate_engineering_bindings(registry)
        self._skill_executor = skill_executor
        self._firewall = PermissionFirewall(
            tuple(item.manifest for item in CANONICAL_AGENT_REGISTRY), grants
        )

    def execute(
        self, task: EngineeringAgentTask, *, now: datetime
    ) -> EngineeringAgentExecution:
        try:
            registration = registration_for(task.invocation.target_id)
        except KeyError as exc:
            raise AgentSecurityError("target agent is unavailable") from exc
        if registration.manifest.team != "engineering":
            raise EngineeringAgentError("SF-8 accepts only canonical engineering agents")

        allowed_skills = ENGINEERING_AGENT_SKILLS.get(registration.manifest.agent_id)
        if allowed_skills is None:
            raise EngineeringAgentError("engineering agent has no SF-8 skill binding")
        if not task.steps:
            raise EngineeringAgentError("engineering agent task requires at least one skill step")

        requested_skill_ids = tuple(step.skill_id for step in task.steps)
        if len(requested_skill_ids) != len(set(requested_skill_ids)):
            raise EngineeringAgentError("engineering agent task cannot repeat a skill step")
        if not set(requested_skill_ids).issubset(allowed_skills):
            raise EngineeringAgentError("engineering agent requested a skill outside its role")

        admission = self._firewall.admit(task.invocation, task.grant, now)
        results: list[SkillExecutionResult] = []
        for step in task.steps:
            results.append(
                self._skill_executor.execute(
                    SkillExecutionRequest(
                        skill_id=step.skill_id,
                        repository=task.repository.resolve(),
                        base_sha=task.base_sha,
                        actor_id=admission.agent_id,
                        tenant_id=task.tenant_id,
                        policy_allowed=task.policy_allowed,
                        payload=step.payload,
                        requested_capabilities=step.requested_capabilities,
                        requested_actions=step.requested_actions,
                        runtime_adapter=step.runtime_adapter,
                    )
                )
            )

        immutable_results = tuple(results)
        review_required = any(
            result.independent_review_required for result in immutable_results
        )
        status = "REVIEW_REQUIRED" if review_required else "READY"
        return EngineeringAgentExecution(
            admission=admission,
            skill_results=immutable_results,
            status=status,
            evidence_digest=_evidence_digest(
                admission, task.base_sha, immutable_results, status
            ),
        )


def _validate_engineering_bindings(registry: SkillRegistry) -> None:
    canonical_engineering_ids = {
        item.manifest.agent_id for item in registrations_for_team("engineering")
    }
    configured_ids = set(ENGINEERING_AGENT_SKILLS)
    if canonical_engineering_ids != configured_ids:
        raise EngineeringAgentError(
            "SF-8 bindings must cover the exact canonical engineering team"
        )

    bound_skills = tuple(
        skill_id
        for agent_id in sorted(ENGINEERING_AGENT_SKILLS)
        for skill_id in ENGINEERING_AGENT_SKILLS[agent_id]
    )
    if len(bound_skills) != len(set(bound_skills)):
        raise EngineeringAgentError("SF-8 primary skill ownership must be unique")
    if set(bound_skills) != set(REQUIRED_SKILL_IDS):
        raise EngineeringAgentError("SF-8 must assign every SF-7 skill exactly once")
    for skill_id in bound_skills:
        registry.resolve(skill_id)


def _evidence_digest(
    admission: AgentAdmissionEvidence,
    base_sha: str,
    results: tuple[SkillExecutionResult, ...],
    status: str,
) -> str:
    material = {
        "agent_id": admission.agent_id,
        "invocation_id": admission.invocation_id,
        "verifier_id": admission.verifier_id,
        "base_sha": base_sha,
        "status": status,
        "skills": [
            {
                "skill_id": result.skill_id,
                "version": result.version,
                "status": result.status,
                "evidence": list(result.emitted_evidence),
                "independent_review_required": result.independent_review_required,
            }
            for result in results
        ],
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
