"""Canonical ILAIOS agent identity registry.

The registry consolidates historical Hermes/ILAKOS/ILATEN role designs behind
stable ILAIOS machine IDs. Human-readable aliases are never orchestration keys.
Registry presence is an identity/governance claim, not proof that a role has a
provider-backed executor; runtime readiness is recorded explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.agent_governance import AgentManifest, AgentStatus


class AgentRegistryError(ValueError):
    """The canonical agent registry violates an identity or governance invariant."""


class RuntimeReadiness(str, Enum):
    REGISTERED = "registered"
    EXECUTABLE = "executable"
    VERIFIED = "verified"


@dataclass(frozen=True, slots=True)
class AgentRegistration:
    manifest: AgentManifest
    readiness: RuntimeReadiness
    backing_capability: str


ORCHESTRATOR_ID = "ilaios.agent.core.orchestrator.v1"
SUPERVISOR_ID = "ilaios.agent.core.supervisor.v1"
SECURITY_VERIFIER_ID = "ilaios.agent.security.verifier.v1"
INDEPENDENT_VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"


def _registration(
    agent_id: str,
    alias: str,
    role: str,
    team: str,
    capabilities: tuple[str, ...],
    permissions: tuple[str, ...],
    backing_capability: str,
    *,
    verifier_id: str = INDEPENDENT_VERIFIER_ID,
    callers: tuple[str, ...] = (ORCHESTRATOR_ID, SUPERVISOR_ID),
    readiness: RuntimeReadiness = RuntimeReadiness.REGISTERED,
) -> AgentRegistration:
    return AgentRegistration(
        AgentManifest(
            agent_id=agent_id,
            alias=alias,
            role=role,
            team=team,
            capabilities=frozenset(capabilities),
            permissions=frozenset(permissions),
            inputs=frozenset({"governed_task", "evidence_reference"}),
            outputs=frozenset({"proposal", "evidence_reference"}),
            dependencies=frozenset({backing_capability}),
            allowed_callers=frozenset(callers),
            allowed_targets=frozenset({agent_id}),
            escalation_path="ilaios.control-plane.supervisor",
            verifier_id=verifier_id,
            version="1.0.0",
            status=AgentStatus.ACTIVE,
        ),
        readiness,
        backing_capability,
    )


CANONICAL_AGENT_REGISTRY: tuple[AgentRegistration, ...] = (
    _registration(
        ORCHESTRATOR_ID,
        "Orchestrator",
        "orchestration",
        "core",
        ("workflow.coordinate", "agent.delegate"),
        ("workflow.read", "agent.invoke"),
        "control-plane",
        callers=("ilaios.control-plane", "human.owner"),
    ),
    _registration(
        "ilaios.agent.core.planner.v1",
        "Planner",
        "planning",
        "core",
        ("workflow.plan",),
        ("workflow.read", "plan.propose"),
        "control-plane",
    ),
    _registration(
        SUPERVISOR_ID,
        "Supervisor",
        "supervision",
        "core",
        ("workflow.supervise", "agent.stop"),
        ("workflow.read", "agent.control"),
        "governance",
        callers=(ORCHESTRATOR_ID, "human.owner"),
    ),
    _registration(
        "ilaios.agent.core.policy.v1",
        "Policy",
        "policy evaluation",
        "core",
        ("policy.evaluate",),
        ("policy.read", "decision.propose"),
        "governance",
    ),
    _registration(
        "ilaios.agent.core.cost-resource.v1",
        "CostResource",
        "cost and resource governance",
        "core",
        ("cost.evaluate", "resource.evaluate"),
        ("usage.read", "budget.propose"),
        "ai-governance",
    ),
    _registration(
        "ilaios.agent.engineering.architect.v1",
        "Daedalus",
        "software architecture",
        "engineering",
        ("architecture.propose",),
        ("repository.read", "design.propose"),
        "software-factory",
    ),
    _registration(
        "ilaios.agent.engineering.core.v1",
        "Hephaestus",
        "core engineering",
        "engineering",
        ("code.propose",),
        ("repository.read", "patch.propose"),
        "software-factory",
    ),
    _registration(
        "ilaios.agent.engineering.frontend.v1",
        "Apollo",
        "frontend engineering",
        "engineering",
        ("frontend.propose",),
        ("repository.read", "patch.propose"),
        "software-factory",
    ),
    _registration(
        "ilaios.agent.engineering.backend.v1",
        "Atlas",
        "backend engineering",
        "engineering",
        ("backend.propose",),
        ("repository.read", "patch.propose"),
        "software-factory",
    ),
    _registration(
        "ilaios.agent.engineering.integration.v1",
        "Integration Bridge",
        "integration engineering",
        "engineering",
        ("integration.propose",),
        ("repository.read", "integration.propose"),
        "software-factory",
    ),
    _registration(
        "ilaios.agent.engineering.test.v1",
        "Dike",
        "test engineering",
        "engineering",
        ("test.design", "test.execute"),
        ("repository.read", "test.propose"),
        "validation",
    ),
    _registration(
        "ilaios.agent.engineering.review.v1",
        "Athena",
        "independent code review",
        "engineering",
        ("code.review",),
        ("repository.read", "review.propose"),
        "validation",
    ),
    _registration(
        "ilaios.agent.engineering.runtime-qa.v1",
        "Argus",
        "runtime quality assurance",
        "engineering",
        ("runtime.verify",),
        ("telemetry.read", "verification.propose"),
        "observability",
    ),
    _registration(
        "ilaios.agent.engineering.release.v1",
        "Janus",
        "release assessment",
        "engineering",
        ("release.assess",),
        ("evidence.read", "release.propose"),
        "deployment",
    ),
    _registration(
        "ilaios.agent.engineering.recovery.v1",
        "Asclepius",
        "recovery engineering",
        "engineering",
        ("recovery.propose",),
        ("evidence.read", "recovery.propose"),
        "operations",
    ),
    _registration(
        "ilaios.agent.security.coordinator.v1",
        "SecurityCoordinator",
        "security coordination",
        "security",
        ("security.coordinate",),
        ("scope.read", "security.delegate"),
        "agent-governance",
        verifier_id=INDEPENDENT_VERIFIER_ID,
    ),
    _registration(
        "ilaios.agent.security.codesec.v1",
        "CodeSec",
        "source code security",
        "security",
        ("security.sast", "security.secret-scan"),
        ("repository.read", "finding.propose"),
        "agent-governance",
        verifier_id=SECURITY_VERIFIER_ID,
    ),
    _registration(
        "ilaios.agent.security.web-api.v1",
        "WebAPISec",
        "web and api security",
        "security",
        ("security.web-api", "security.dast"),
        ("authorized-target.read", "finding.propose"),
        "agent-governance",
        verifier_id=SECURITY_VERIFIER_ID,
    ),
    _registration(
        "ilaios.agent.security.supply-chain.v1",
        "SupplyChainSec",
        "software supply-chain security",
        "security",
        ("security.dependency", "security.sbom"),
        ("repository.read", "finding.propose"),
        "agent-governance",
        verifier_id=SECURITY_VERIFIER_ID,
    ),
    _registration(
        "ilaios.agent.security.infrastructure.v1",
        "InfrastructureSec",
        "infrastructure security",
        "security",
        ("security.infrastructure",),
        ("authorized-config.read", "finding.propose"),
        "agent-governance",
        verifier_id=SECURITY_VERIFIER_ID,
    ),
    _registration(
        SECURITY_VERIFIER_ID,
        "SecurityVerifier",
        "independent security verification",
        "security",
        ("security.verify",),
        ("evidence.read", "verification.propose"),
        "validation",
        verifier_id=INDEPENDENT_VERIFIER_ID,
    ),
    _registration(
        "ilaios.agent.web.ux.v1",
        "WebUX",
        "web user experience",
        "web",
        ("web.ux",),
        ("requirements.read", "design.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.web.visual.v1",
        "WebVisual",
        "web visual design",
        "web",
        ("web.visual",),
        ("requirements.read", "design.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.web.asset.v1",
        "WebAsset",
        "web asset preparation",
        "web",
        ("web.asset",),
        ("asset.read", "asset.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.web.content.v1",
        "WebContent",
        "web content",
        "web",
        ("web.content",),
        ("requirements.read", "content.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.web.seo.v1",
        "WebSEO",
        "search optimization",
        "web",
        ("web.seo",),
        ("site.read", "seo.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.web.browser-qa.v1",
        "BrowserQA",
        "browser quality assurance",
        "web",
        ("web.verify",),
        ("authorized-site.read", "verification.propose"),
        "web-factory",
    ),
    _registration(
        "ilaios.agent.media.story.v1",
        "Story",
        "story development",
        "media",
        ("media.story",),
        ("brief.read", "script.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.scene-director.v1",
        "SceneDirector",
        "scene direction",
        "media",
        ("media.scene-plan",),
        ("script.read", "scene-plan.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.generation.v1",
        "MediaGeneration",
        "media generation",
        "media",
        ("media.generate",),
        ("shot-plan.read", "asset.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.voice-audio.v1",
        "VoiceAudio",
        "voice and audio",
        "media",
        ("media.audio",),
        ("script.read", "audio.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.editor.v1",
        "Editor",
        "media editing",
        "media",
        ("media.assemble",),
        ("asset.read", "timeline.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.qa.v1",
        "MediaQA",
        "media quality assurance",
        "media",
        ("media.verify",),
        ("artifact.read", "verification.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.social-metadata.v1",
        "SocialMetadata",
        "social metadata",
        "media",
        ("social.metadata",),
        ("artifact.read", "metadata.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.media.publishing.v1",
        "Publishing",
        "governed publishing",
        "media",
        ("social.publish-propose",),
        ("artifact.read", "publish.propose"),
        "video-factory",
    ),
    _registration(
        "ilaios.agent.intelligence.research.v1",
        "Research",
        "research",
        "intelligence",
        ("research.collect",),
        ("source.read", "research.propose"),
        "knowledge",
    ),
    _registration(
        "ilaios.agent.intelligence.fact-check.v1",
        "FactCheck",
        "fact checking",
        "intelligence",
        ("research.verify",),
        ("source.read", "verification.propose"),
        "knowledge",
    ),
    _registration(
        "ilaios.agent.intelligence.data-analyst.v1",
        "DataAnalyst",
        "data analysis",
        "intelligence",
        ("data.analyze",),
        ("data.read", "analysis.propose"),
        "knowledge",
    ),
    _registration(
        "ilaios.agent.intelligence.knowledge.v1",
        "Knowledge",
        "knowledge curation",
        "intelligence",
        ("knowledge.curate",),
        ("evidence.read", "knowledge.propose"),
        "knowledge",
    ),
    _registration(
        "ilaios.agent.operations.automation.v1",
        "Automation",
        "operations automation",
        "operations",
        ("operations.automate",),
        ("workflow.read", "automation.propose"),
        "operations",
    ),
    _registration(
        "ilaios.agent.operations.analytics.v1",
        "Analytics",
        "operations analytics",
        "operations",
        ("operations.analyze",),
        ("telemetry.read", "analysis.propose"),
        "observability",
    ),
    _registration(
        "ilaios.agent.operations.monitoring.v1",
        "Monitoring",
        "operations monitoring",
        "operations",
        ("operations.monitor",),
        ("telemetry.read", "alert.propose"),
        "observability",
    ),
    _registration(
        "ilaios.agent.operations.recovery.v1",
        "OperationsRecovery",
        "operations recovery",
        "operations",
        ("operations.recover",),
        ("evidence.read", "recovery.propose"),
        "operations",
    ),
    _registration(
        "ilaios.agent.operations.provider-watcher.v1",
        "ProviderWatcher",
        "provider health monitoring",
        "operations",
        ("provider.monitor",),
        ("provider-health.read", "routing.propose"),
        "runtime-routing",
    ),
    _registration(
        "ilaios.agent.operations.benchmark.v1",
        "Benchmark",
        "provider and capability benchmarking",
        "operations",
        ("benchmark.evaluate",),
        ("benchmark-input.read", "benchmark.propose"),
        "runtime-routing",
    ),
    _registration(
        INDEPENDENT_VERIFIER_ID,
        "IndependentVerifier",
        "independent verification",
        "meta",
        ("evidence.verify",),
        ("evidence.read", "verification.propose"),
        "validation",
        verifier_id="human.owner",
        callers=(ORCHESTRATOR_ID, SUPERVISOR_ID, SECURITY_VERIFIER_ID),
    ),
    _registration(
        "ilaios.agent.meta.self-development.v1",
        "SelfDevelopmentCoordinator",
        "controlled self-development coordination",
        "meta",
        ("self-development.coordinate",),
        ("repository.read", "change.propose"),
        "software-factory",
        verifier_id=INDEPENDENT_VERIFIER_ID,
    ),
)


def validate_agent_registry(
    registrations: tuple[AgentRegistration, ...] = CANONICAL_AGENT_REGISTRY,
) -> None:
    ids = [item.manifest.agent_id for item in registrations]
    if len(ids) != len(set(ids)):
        raise AgentRegistryError("agent IDs must be globally unique")
    known = set(ids)
    for item in registrations:
        manifest = item.manifest
        if not manifest.agent_id.startswith("ilaios.agent."):
            raise AgentRegistryError("active machine IDs must use the ILAIOS namespace")
        if any(
            legacy in manifest.agent_id.casefold()
            for legacy in ("hermes", "ilakos", "ilaten")
        ):
            raise AgentRegistryError("legacy product names are forbidden in machine IDs")
        if manifest.verifier_id not in known and not manifest.verifier_id.startswith("human."):
            raise AgentRegistryError("verifier must resolve to a registered agent or human authority")
        if item.readiness is RuntimeReadiness.REGISTERED and manifest.status is not AgentStatus.ACTIVE:
            raise AgentRegistryError("registered canonical manifests must be available to governance")
        if not item.backing_capability:
            raise AgentRegistryError("backing capability is required")


def registration_for(agent_id: str) -> AgentRegistration:
    for registration in CANONICAL_AGENT_REGISTRY:
        if registration.manifest.agent_id == agent_id:
            return registration
    raise KeyError(agent_id)


def registrations_for_team(team: str) -> tuple[AgentRegistration, ...]:
    return tuple(
        item for item in CANONICAL_AGENT_REGISTRY if item.manifest.team == team
    )


validate_agent_registry()
