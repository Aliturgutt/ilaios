"""First-party proposal skills for canonical Operations 6 + Meta SelfDevelopment.

These skills are additive proposal contracts on the existing GovernedRuntime.
They do not grant operational mutation, provider routing, recovery execution,
repository mutation, evidence promotion, deployment, or self-modification authority.
IndependentVerifier continues to use the existing canonical verifier skill.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.agent_registry import INDEPENDENT_VERIFIER_ID, registration_for
from services.named_agent_executor import NamedAgentExecutor
from services.operations_meta_agent_execution import operations_meta_binding_for


class OperationsMetaSkillCatalogError(ValueError):
    """Operations/Meta skill identity or authority drifted."""


@dataclass(frozen=True, slots=True)
class OperationsMetaSkillDefinition:
    skill_id: str
    owner_agent_id: str
    capability: str
    instructions: str

    def content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"


OPERATIONS_META_FIRST_PARTY_SKILLS: tuple[OperationsMetaSkillDefinition, ...] = (
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.automation.v1",
        "ilaios.agent.operations.automation.v1",
        "operations.automate",
        """You are the canonical ILAIOS Automation operations agent. Produce only a bounded automation proposal from admitted workflow evidence. Describe trigger, prerequisites, deterministic steps, failure handling, rollback and required approvals. Do not execute workflows, mutate systems, publish, spend, deploy, change policy, or bypass Tool Gateway and evidence controls.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.analytics.v1",
        "ilaios.agent.operations.analytics.v1",
        "operations.analyze",
        """You are the canonical ILAIOS Operations Analytics agent. Analyze only admitted telemetry and evidence. Return bounded observations, trends, confidence, anomalies and recommended next checks. Do not invent telemetry, mutate dashboards, change runtime state, route providers, or promote maturity.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.monitoring.v1",
        "ilaios.agent.operations.monitoring.v1",
        "operations.monitor",
        """You are the canonical ILAIOS Monitoring agent. Evaluate supplied telemetry against declared health and SLO evidence and produce alert proposals only. Do not contact external targets, alter monitors, restart services, recover systems, or claim health without evidence.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.recovery.v1",
        "ilaios.agent.operations.recovery.v1",
        "operations.recover",
        """You are the canonical ILAIOS OperationsRecovery planning agent. From admitted failure evidence, propose the smallest bounded recovery sequence, safety checks, rollback and verification. You have no direct recovery or mutation authority. Execution remains behind canonical Policy, Approval, Tool Gateway and evidence gates.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.provider-watcher.v1",
        "ilaios.agent.operations.provider-watcher.v1",
        "provider.monitor",
        """You are the canonical ILAIOS ProviderWatcher. Analyze only supplied provider-health evidence and propose routing-health observations. Never change provider routing, credentials, budgets, model policy or provider configuration. Canonical routing and UsageGovernor remain authoritative.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.operations.benchmark.v1",
        "ilaios.agent.operations.benchmark.v1",
        "benchmark.evaluate",
        """You are the canonical ILAIOS Benchmark agent. Evaluate admitted benchmark evidence against explicit capability, quality, cost and latency criteria. Return a reproducible comparison proposal only. Do not run unapproved workloads, spend budget, change routing, or promote a provider without evidence.""",
    ),
    OperationsMetaSkillDefinition(
        "ilaios.skill.meta.self-development.v1",
        "ilaios.agent.meta.self-development.v1",
        "self-development.coordinate",
        """You are the canonical ILAIOS SelfDevelopmentCoordinator. Inspect only admitted repository and evidence context and propose bounded improvements, dependencies, tests and rollback. Never modify your own authority, rewrite Core, bypass governance, mutate repositories, merge, deploy, self-approve, or claim implementation without external evidence.""",
    ),
)


def ensure_operations_meta_agent_skills(
    executor: NamedAgentExecutor,
) -> dict[str, str]:
    """Provision exact Operations/Meta proposal skills into the existing runtime."""
    validate_operations_meta_skill_catalog()
    digests: dict[str, str] = {}
    for item in OPERATIONS_META_FIRST_PARTY_SKILLS:
        executor.ensure_agent(item.owner_agent_id)
        digests[item.skill_id] = executor.ensure_skill(
            item.skill_id,
            item.content(),
            frozenset({item.capability}),
        )
    return digests


def validate_operations_meta_skill_catalog() -> None:
    ids = [item.skill_id for item in OPERATIONS_META_FIRST_PARTY_SKILLS]
    owners = [item.owner_agent_id for item in OPERATIONS_META_FIRST_PARTY_SKILLS]
    if len(ids) != 7 or len(ids) != len(set(ids)):
        raise OperationsMetaSkillCatalogError(
            "Operations/Meta first-party catalog must contain seven unique provider skills"
        )
    if len(owners) != 7 or len(owners) != len(set(owners)):
        raise OperationsMetaSkillCatalogError(
            "Operations/Meta provider skill ownership must be one-to-one"
        )
    if INDEPENDENT_VERIFIER_ID in owners:
        raise OperationsMetaSkillCatalogError(
            "IndependentVerifier must remain outside provider-backed skill catalog"
        )
    for item in OPERATIONS_META_FIRST_PARTY_SKILLS:
        binding = operations_meta_binding_for(item.owner_agent_id)
        registration = registration_for(item.owner_agent_id)
        if binding.primary_skill_id != item.skill_id:
            raise OperationsMetaSkillCatalogError(
                "first-party skill identity diverges from Operations/Meta binding"
            )
        if binding.capability != item.capability:
            raise OperationsMetaSkillCatalogError(
                "first-party skill capability diverges from Operations/Meta binding"
            )
        if item.capability not in registration.manifest.capabilities:
            raise OperationsMetaSkillCatalogError(
                "first-party skill capability exceeds owner manifest"
            )
        if not item.instructions.strip():
            raise OperationsMetaSkillCatalogError("skill instructions cannot be blank")

    verifier = operations_meta_binding_for(INDEPENDENT_VERIFIER_ID)
    if verifier.primary_skill_id != "ilaios.skill.meta.independent-verification.v1":
        raise OperationsMetaSkillCatalogError(
            "IndependentVerifier must reuse the canonical verifier skill"
        )
    if verifier.execution_mode != "independent-verification":
        raise OperationsMetaSkillCatalogError(
            "IndependentVerifier execution mode drifted"
        )


validate_operations_meta_skill_catalog()

__all__ = [
    "OPERATIONS_META_FIRST_PARTY_SKILLS",
    "OperationsMetaSkillCatalogError",
    "ensure_operations_meta_agent_skills",
    "validate_operations_meta_skill_catalog",
]
