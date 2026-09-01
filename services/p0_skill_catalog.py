"""Canonical first-party skill provisioning for P0 named agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import INDEPENDENT_VERIFIER_ID, registration_for
from services.named_agent_executor import NamedAgentExecutor
from services.p0_agent_execution import P0_AGENT_BINDINGS, binding_for
from services.software_factory_skills import SkillRegistry, default_skills_root


class P0SkillCatalogError(ValueError):
    """P0 skill identity/ownership drifted from canonical agent bindings."""


@dataclass(frozen=True, slots=True)
class P0SkillDefinition:
    skill_id: str
    owner_agent_id: str
    capability: str
    instructions: str

    def content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"


P0_FIRST_PARTY_SKILLS: tuple[P0SkillDefinition, ...] = (
    P0SkillDefinition(
        "ilaios.skill.core.orchestration.v1",
        "ilaios.agent.core.orchestrator.v1",
        "workflow.coordinate",
        """You are the canonical ILAIOS Orchestrator. Coordinate only governed tasks and canonical agent IDs. Decompose work into bounded delegations; do not bypass Supervisor, Policy, approval, tenant, security, cost, evidence, or execution-grant boundaries. Never create another Core, scheduler, router, policy engine, or agent engine. Never claim execution, verification, deployment, or production without supplied evidence. Return a machine-readable coordination proposal only; side effects require the existing governed runtime.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.core.planning.v1",
        "ilaios.agent.core.planner.v1",
        "workflow.plan",
        """You are the canonical ILAIOS Planner. Convert the admitted objective into a bounded dependency-aware plan using only known capabilities. Separate analysis, implementation, validation, independent review, recovery, and release gates. Do not execute side effects, invent credentials, choose unauthorized providers, or promote maturity. State unresolved assumptions and required evidence explicitly.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.core.supervision.v1",
        "ilaios.agent.core.supervisor.v1",
        "workflow.supervise",
        """You are the canonical ILAIOS Supervisor. Evaluate observed execution evidence, detect stalled/unsafe/over-budget work, and propose continue, stop, retry, recover, or escalate decisions. Platform policy and execution grants remain authoritative. Never approve your own output as VERIFIED and never mutate production directly.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.core.policy.v1",
        "ilaios.agent.core.policy.v1",
        "policy.evaluate",
        """You are the ILAIOS Policy analysis agent. Produce an advisory policy interpretation from the supplied policy/evidence only. You are not the authorization engine: deterministic platform policy, grants, approvals, tenant boundaries, DLP and security gates are authoritative and may reject your proposal. Default to deny when required evidence is absent or contradictory.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.core.cost-resource.v1",
        "ilaios.agent.core.cost-resource.v1",
        "cost.evaluate",
        """You are the ILAIOS CostResource analysis agent. Assess bounded resource and cost options from supplied usage, quota and price evidence. Never invent free pricing or authorize spend. Canonical UsageGovernor/budget controls are authoritative. Prefer lower-cost eligible routes only when capability, quality, policy and evidence gates remain satisfied; otherwise fail closed or escalate.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.coordinate.v1",
        "ilaios.agent.security.coordinator.v1",
        "security.coordinate",
        """You are the defensive ILAIOS SecurityCoordinator. Coordinate only explicitly authorized security scope among CodeSec, WebAPISec, SupplyChainSec, InfrastructureSec and SecurityVerifier. Do not request exploitation, credential bypass, arbitrary Internet scanning, persistence, destructive actions or production mutation. Every finding must retain source evidence and independent verification.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.sast.v1",
        "ilaios.agent.security.codesec.v1",
        "security.sast",
        """Deterministic CodeSec skill binding. Analyze only the authorized repository through the canonical SecurityFactory source/secret rules. No network access, exploit execution, credential retrieval, repository mutation or self-verification is permitted. Return observed findings and remediation evidence only.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.web-api.v1",
        "ilaios.agent.security.web-api.v1",
        "security.web-api",
        """Deterministic WebAPISec skill binding. Analyze only supplied non-destructive HTTP observations for explicitly allowed localhost/test targets through SecurityFactory. Never initiate arbitrary external scans, bypass authentication, exploit a target or broaden scope.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.supply-chain.v1",
        "ilaios.agent.security.supply-chain.v1",
        "security.dependency",
        """Deterministic SupplyChainSec skill binding. Analyze dependency and package metadata only inside the authorized repository using canonical SecurityFactory rules. Report provenance/pinning risks; do not install packages, execute dependencies, access external registries, or mutate lockfiles.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.infrastructure.v1",
        "ilaios.agent.security.infrastructure.v1",
        "security.infrastructure",
        """Deterministic InfrastructureSec skill binding. Analyze authorized repository configuration for bounded infrastructure-policy risks using SecurityFactory. Do not contact cloud control planes, change infrastructure, retrieve secrets, or expand target scope.""",
    ),
    P0SkillDefinition(
        "ilaios.skill.security.verify.v1",
        "ilaios.agent.security.verifier.v1",
        "security.verify",
        """Deterministic SecurityVerifier binding. Independently evaluate the exact persisted producer report. Producer and verifier identities must differ. A report with HIGH/CRITICAL blocking findings cannot pass. Do not modify findings, broaden scope, execute remediation, or self-certify.""",
    ),
)

INDEPENDENT_VERIFIER_SKILL = P0SkillDefinition(
    "ilaios.skill.meta.independent-verification.v1",
    INDEPENDENT_VERIFIER_ID,
    "evidence.verify",
    """You are the canonical ILAIOS IndependentVerifier. Evaluate only the supplied producer evidence envelope against the requested acceptance contract. You must be a different identity from the producer. Return strict JSON with verdict PASS or FAIL, the exact producer_evidence_digest, and findings. PASS requires no unresolved findings. Never execute producer work, alter evidence, invent missing evidence, or promote a result beyond what the supplied proof supports.""",
)


def provision_non_engineering_p0_skills(executor: NamedAgentExecutor) -> dict[str, str]:
    validate_p0_skill_catalog()
    return {
        item.skill_id: executor.provision_skill(
            item.skill_id, item.content(), frozenset({item.capability})
        )
        for item in P0_FIRST_PARTY_SKILLS
    }


def ensure_non_engineering_p0_skills(executor: NamedAgentExecutor) -> dict[str, str]:
    validate_p0_skill_catalog()
    return {
        item.skill_id: executor.ensure_skill(
            item.skill_id, item.content(), frozenset({item.capability})
        )
        for item in (*P0_FIRST_PARTY_SKILLS, INDEPENDENT_VERIFIER_SKILL)
    }


def provision_engineering_primary_skills(
    executor: NamedAgentExecutor,
    repository_root: Path,
) -> dict[str, str]:
    return _engineering_primary_skills(
        executor, default_skills_root(repository_root), ensure=False
    )


def ensure_engineering_primary_skills(
    executor: NamedAgentExecutor,
    skills_root: Path,
) -> dict[str, str]:
    return _engineering_primary_skills(executor, skills_root.resolve(), ensure=True)


def _engineering_primary_skills(
    executor: NamedAgentExecutor,
    skills_root: Path,
    *,
    ensure: bool,
) -> dict[str, str]:
    registry = SkillRegistry(skills_root)
    digests: dict[str, str] = {}
    for binding in P0_AGENT_BINDINGS:
        registration = registration_for(binding.agent_id)
        if registration.manifest.team != "engineering":
            continue
        package = registry.resolve(binding.primary_skill_id)
        instructions = (package.root / "SKILL.md").read_bytes()
        if not instructions.strip():
            raise P0SkillCatalogError(
                f"empty canonical Engineering skill instructions: {binding.primary_skill_id}"
            )
        digest = (
            executor.ensure_skill(
                binding.primary_skill_id,
                instructions,
                frozenset({binding.capability}),
            )
            if ensure
            else executor.provision_skill(
                binding.primary_skill_id,
                instructions,
                frozenset({binding.capability}),
            )
        )
        digests[binding.primary_skill_id] = digest
    if len(digests) != 10:
        raise P0SkillCatalogError("Engineering primary provisioning must cover 10 agents")
    return digests


def validate_p0_skill_catalog() -> None:
    expected_ids = {
        binding.primary_skill_id
        for binding in P0_AGENT_BINDINGS
        if registration_for(binding.agent_id).manifest.team in {"core", "security"}
    }
    actual_ids = {item.skill_id for item in P0_FIRST_PARTY_SKILLS}
    if actual_ids != expected_ids:
        raise P0SkillCatalogError(
            f"Core/Security skill coverage mismatch missing={sorted(expected_ids-actual_ids)} "
            f"extra={sorted(actual_ids-expected_ids)}"
        )
    if len(actual_ids) != len(P0_FIRST_PARTY_SKILLS):
        raise P0SkillCatalogError("P0 skill IDs must be unique")
    owners = [item.owner_agent_id for item in P0_FIRST_PARTY_SKILLS]
    if len(owners) != len(set(owners)):
        raise P0SkillCatalogError("Core/Security primary skill ownership must be unique")
    for item in P0_FIRST_PARTY_SKILLS:
        binding = binding_for(item.owner_agent_id)
        registration = registration_for(item.owner_agent_id)
        if binding.primary_skill_id != item.skill_id:
            raise P0SkillCatalogError("skill identity diverges from P0 binding")
        if binding.capability != item.capability:
            raise P0SkillCatalogError("skill capability diverges from P0 binding")
        if item.capability not in registration.manifest.capabilities:
            raise P0SkillCatalogError("skill capability exceeds agent manifest")
        if not item.instructions.strip():
            raise P0SkillCatalogError("skill instructions must not be blank")
    verifier = registration_for(INDEPENDENT_VERIFIER_SKILL.owner_agent_id)
    if INDEPENDENT_VERIFIER_SKILL.capability not in verifier.manifest.capabilities:
        raise P0SkillCatalogError("IndependentVerifier skill exceeds manifest")
    if not INDEPENDENT_VERIFIER_SKILL.instructions.strip():
        raise P0SkillCatalogError("IndependentVerifier instructions must not be blank")


validate_p0_skill_catalog()
