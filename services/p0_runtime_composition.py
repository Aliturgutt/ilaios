"""Single-runtime composition root for the P0 canonical agent population."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from services.agent_governance import GrantAuthorizer
from services.agent_readiness import p0_registrations
from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.named_agent_executor import NamedAgentExecutor
from services.p0_agent_execution import P0ProviderBackedExecutor, P0_AGENT_BINDINGS
from services.p0_skill_catalog import (
    ensure_engineering_primary_skills,
    ensure_non_engineering_p0_skills,
)
from services.runtime import GovernedRuntime
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter
from services.security_agent_execution import (
    DefensiveSecurityAgentExecutor,
    security_local_provider_specs,
)


class P0RuntimeCompositionError(RuntimeError):
    """P0 composition would violate canonical runtime or provider boundaries."""


@dataclass(frozen=True, slots=True)
class P0RuntimeComposition:
    named_executor: NamedAgentExecutor
    security_executor: DefensiveSecurityAgentExecutor
    ai_executor: P0ProviderBackedExecutor | None
    target_agent_count: int
    provisioned_identity_count: int
    skill_count: int
    security_provider_count: int
    ai_provider_count: int

    @property
    def ai_configured(self) -> bool:
        return self.ai_executor is not None


def compose_p0_runtime(
    runtime: GovernedRuntime,
    grants: GrantAuthorizer,
    *,
    engineering_skills_root: Path,
    ai_adapter: GovernedAIProviderAdapter | None = None,
    ai_provider_capabilities: Mapping[str, frozenset[str]] | None = None,
) -> P0RuntimeComposition:
    p0 = p0_registrations()
    if len(p0) != 21:
        raise P0RuntimeCompositionError("canonical P0 population must contain 21 agents")

    named = NamedAgentExecutor(runtime, grants)
    target_ids = {item.manifest.agent_id for item in p0}
    identities = target_ids | {INDEPENDENT_VERIFIER_ID}
    for agent_id in sorted(identities):
        named.ensure_agent(agent_id)

    core_security = ensure_non_engineering_p0_skills(named)
    engineering = ensure_engineering_primary_skills(named, engineering_skills_root)
    all_skill_ids = set(core_security) | set(engineering)
    if len(core_security) != 12 or len(engineering) != 10 or len(all_skill_ids) != 22:
        raise P0RuntimeCompositionError("P0 plus verifier dependency skill coverage drifted")

    security_specs = security_local_provider_specs()
    for provider_id, adapter_kind, capability in security_specs:
        named.ensure_provider(
            provider_id,
            frozenset({capability}),
            adapter_kind=adapter_kind,
            deterministic=True,
        )

    ai_executor: P0ProviderBackedExecutor | None = None
    ai_provider_count = 0
    capabilities = dict(ai_provider_capabilities or {})
    if ai_adapter is None:
        if capabilities:
            raise P0RuntimeCompositionError(
                "AI provider capabilities cannot be supplied without a governed adapter"
            )
    else:
        if not capabilities:
            raise P0RuntimeCompositionError(
                "governed AI adapter requires explicit provider capability contracts"
            )
        governed_ai_capabilities = {
            binding.capability
            for binding in P0_AGENT_BINDINGS
            if binding.execution_mode == "governed-ai"
        }
        for provider_id, provider_capabilities in sorted(capabilities.items()):
            if not provider_capabilities:
                raise P0RuntimeCompositionError("AI provider capability set cannot be empty")
            if not provider_capabilities.issubset(
                governed_ai_capabilities | {"evidence.verify"}
            ):
                raise P0RuntimeCompositionError(
                    "AI provider capability contract exceeds P0 governed execution"
                )
            named.ensure_provider(
                provider_id,
                provider_capabilities,
                adapter_kind=ai_adapter.adapter_kind(provider_id),
                deterministic=False,
            )
        ai_provider_count = len(capabilities)
        ai_executor = P0ProviderBackedExecutor(named, ai_adapter)

    return P0RuntimeComposition(
        named_executor=named,
        security_executor=DefensiveSecurityAgentExecutor(named),
        ai_executor=ai_executor,
        target_agent_count=len(p0),
        provisioned_identity_count=len(identities),
        skill_count=len(all_skill_ids),
        security_provider_count=len(security_specs),
        ai_provider_count=ai_provider_count,
    )
