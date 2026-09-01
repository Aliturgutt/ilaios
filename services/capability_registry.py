"""Canonical ILAIOS capability identity registry.

Legacy system names are provenance only. Active orchestration and dependency
contracts bind to stable ``ilaios.capability.*`` IDs so a historical rename can
never create parallel runtimes or duplicate authority.
"""

from __future__ import annotations

from dataclasses import dataclass


class CapabilityRegistryError(ValueError):
    """The canonical capability registry violates a consolidation invariant."""


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    capability_id: str
    display_name: str
    domain: str
    dependencies: frozenset[str]
    implementation_roots: tuple[str, ...]
    legacy_sources: frozenset[str]


CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        "ilaios.capability.core",
        "Core Platform",
        "platform",
        frozenset(),
        ("src/core", "services/control_plane"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.identity-tenant",
        "Identity and Tenant Boundary",
        "platform",
        frozenset({"ilaios.capability.core"}),
        ("services/identity.py",),
        frozenset({"ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.workflow-runtime",
        "Workflow and Durable Runtime",
        "platform",
        frozenset({"ilaios.capability.core"}),
        ("services/runtime", "services/control_plane"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.policy-governance",
        "Policy, Approval and Governance",
        "platform",
        frozenset({"ilaios.capability.identity-tenant"}),
        ("services/governance", "services/agent_governance.py", "services/ai_governance.py"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.evidence-audit",
        "Evidence, Audit and Provenance",
        "platform",
        frozenset({"ilaios.capability.core"}),
        ("src/core", "services/evidence"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.privacy-dlp",
        "Privacy and DLP",
        "security",
        frozenset({"ilaios.capability.identity-tenant"}),
        ("services/privacy.py",),
        frozenset({"ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.secrets-crypto",
        "Secrets and Cryptography",
        "security",
        frozenset({"ilaios.capability.identity-tenant"}),
        ("services/cryptography.py",),
        frozenset({"ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.observability-operations",
        "Observability, Operations and Recovery",
        "operations",
        frozenset({"ilaios.capability.workflow-runtime"}),
        ("services/observability.py", "services/operations.py", "services/operational_drills.py"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.agent-governance",
        "Agent Governance and Permission Firewall",
        "agents",
        frozenset({"ilaios.capability.policy-governance"}),
        ("services/agent_governance.py", "services/agent_registry.py"),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.provider-routing",
        "Provider Routing and Cost Governance",
        "agents",
        frozenset({"ilaios.capability.policy-governance"}),
        ("services/runtime/routing.py", "services/ai_governance.py"),
        frozenset({"ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.code-intelligence",
        "Code Intelligence",
        "intelligence",
        frozenset({"ilaios.capability.core"}),
        ("src/code_intelligence",),
        frozenset({"Hermes", "ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.knowledge",
        "Knowledge / RAG and Project Context",
        "intelligence",
        frozenset(
            {
                "ilaios.capability.core",
                "ilaios.capability.identity-tenant",
                "ilaios.capability.privacy-dlp",
                "ilaios.capability.evidence-audit",
                "ilaios.capability.provider-routing",
            }
        ),
        ("src/knowledge_graph", "src/project_manager", "services/knowledge_rag.py"),
        frozenset({"Hermes", "ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.video-media-factory",
        "Video and Media Factory",
        "factory",
        frozenset(
            {
                "ilaios.capability.workflow-runtime",
                "ilaios.capability.evidence-audit",
                "ilaios.capability.provider-routing",
            }
        ),
        ("src/video_automation",),
        frozenset({"Hermes", "ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.web-factory",
        "Web Factory",
        "factory",
        frozenset(
            {
                "ilaios.capability.workflow-runtime",
                "ilaios.capability.policy-governance",
            }
        ),
        ("services/integrations/web_factory.py",),
        frozenset({"Hermes", "ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.software-factory",
        "Software Factory",
        "factory",
        frozenset(
            {
                "ilaios.capability.workflow-runtime",
                "ilaios.capability.policy-governance",
            }
        ),
        ("services/software_factory.py",),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.security-factory",
        "Security Factory",
        "factory",
        frozenset(
            {
                "ilaios.capability.agent-governance",
                "ilaios.capability.evidence-audit",
            }
        ),
        ("services/security_factory.py",),
        frozenset({"Hermes", "ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.app-factory",
        "App Factory",
        "factory",
        frozenset({"ilaios.capability.software-factory"}),
        ("services/app_factory.py",),
        frozenset({"ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.research-data",
        "Research and Data",
        "factory",
        frozenset({"ilaios.capability.knowledge"}),
        ("services/research_data_factory.py",),
        frozenset({"ILAKOS", "ILATEN"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.creative-document",
        "Creative and Document",
        "factory",
        frozenset({"ilaios.capability.workflow-runtime"}),
        ("services/creative_document_factory.py",),
        frozenset({"ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.commerce-growth",
        "Commerce and Growth",
        "factory",
        frozenset({"ilaios.capability.workflow-runtime"}),
        ("services/commerce_growth_factory.py",),
        frozenset({"ILAKOS"}),
    ),
    CapabilityDefinition(
        "ilaios.capability.personal-operations",
        "Personal Operations and Automation",
        "factory",
        frozenset({"ilaios.capability.workflow-runtime"}),
        ("services/personal_operations_factory.py",),
        frozenset({"Hermes", "ILAKOS"}),
    ),
)


def validate_capability_registry(
    capabilities: tuple[CapabilityDefinition, ...] = CAPABILITIES,
) -> None:
    ids = [item.capability_id for item in capabilities]
    if len(ids) != len(set(ids)):
        raise CapabilityRegistryError("capability IDs must be globally unique")
    known = set(ids)
    for capability in capabilities:
        if not capability.capability_id.startswith("ilaios.capability."):
            raise CapabilityRegistryError("active capability IDs must use ILAIOS namespace")
        if any(
            legacy in capability.capability_id.casefold()
            for legacy in ("hermes", "ilakos", "ilaten")
        ):
            raise CapabilityRegistryError("legacy names are provenance only")
        unknown = capability.dependencies - known
        if unknown:
            raise CapabilityRegistryError(
                f"unknown dependencies for {capability.capability_id}: {sorted(unknown)}"
            )
        if not capability.display_name or not capability.domain:
            raise CapabilityRegistryError("display name and domain are required")


def capability(capability_id: str) -> CapabilityDefinition:
    for definition in CAPABILITIES:
        if definition.capability_id == capability_id:
            return definition
    raise KeyError(capability_id)


def capabilities_for_domain(domain: str) -> tuple[CapabilityDefinition, ...]:
    return tuple(item for item in CAPABILITIES if item.domain == domain)


validate_capability_registry()
