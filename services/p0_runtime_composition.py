"""Single-runtime composition root for the P0 canonical agent population."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from services.agent_governance import GrantAuthorizer
from services.agent_provider_capabilities import AGENT_GOVERNED_AI_CAPABILITIES
from services.agent_readiness import p0_registrations
from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.independent_verifier_execution import (
    INDEPENDENT_VERIFIER_ADAPTER_KIND,
    INDEPENDENT_VERIFIER_PROVIDER_ID,
)
from services.named_agent_executor import NamedAgentExecutor
from services.p0_agent_execution import P0ProviderBackedExecutor
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
from services.security_methodology_skills import (
    default_security_methodology_skills_root,
    ensure_security_methodology_skills,
)
from services.skill_engineering_catalog import default_skill_engineering_root
from services.skill_engineering_runtime import ensure_skill_engineering_runtime_skills


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
    skill_engineering_skill_count: int
    security_provider_count: int
    verifier_provider_count: int
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
        raise P0RuntimeCompositionError(
            "canonical P0 population must contain 21 agents"
        )

    named = NamedAgentExecutor(runtime, grants)
    target_ids = {item.manifest.agent_id for item in p0}
    identities = target_ids | {INDEPENDENT_VERIFIER_ID}
    for agent_id in sorted(identities):
        named.ensure_agent(agent_id)

    engineering_root = engineering_skills_root.resolve()
    repository_root = _repository_root_from_engineering_skills(engineering_root)
    core_security = ensure_non_engineering_p0_skills(named)
    engineering = ensure_engineering_primary_skills(named, engineering_root)
    security_methodology = ensure_security_methodology_skills(
        named,
        default_security_methodology_skills_root(repository_root),
    )
    skill_engineering = ensure_skill_engineering_runtime_skills(
        named,
        default_skill_engineering_root(repository_root),
    )
    all_skill_ids = (
        set(core_security)
        | set(engineering)
        | set(security_methodology)
        | set(skill_engineering)
    )
    if (
        len(core_security) != 12
        or len(engineering) != 10
        or len(security_methodology) != 6
        or len(skill_engineering) != 5
        or len(all_skill_ids) != 33
    ):
        raise P0RuntimeCompositionError(
            "P0 plus verifier/security/skill-engineering coverage drifted"
        )

    security_specs = security_local_provider_specs()
    for provider_id, adapter_kind, capability in security_specs:
        named.ensure_provider(
            provider_id,
            frozenset({capability}),
            adapter_kind=adapter_kind,
            deterministic=True,
        )

    named.ensure_provider(
        INDEPENDENT_VERIFIER_PROVIDER_ID,
        frozenset({"evidence.verify"}),
        adapter_kind=INDEPENDENT_VERIFIER_ADAPTER_KIND,
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
        for provider_id, provider_capabilities in sorted(capabilities.items()):
            if not provider_capabilities:
                raise P0RuntimeCompositionError(
                    "AI provider capability set cannot be empty"
                )
            if not provider_capabilities.issubset(AGENT_GOVERNED_AI_CAPABILITIES):
                raise P0RuntimeCompositionError(
                    "AI provider capability contract exceeds canonical governed execution"
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
        skill_engineering_skill_count=len(skill_engineering),
        security_provider_count=len(security_specs),
        verifier_provider_count=1,
        ai_provider_count=ai_provider_count,
    )


def _repository_root_from_engineering_skills(skills_root: Path) -> Path:
    expected_suffix = ("tools", "software-factory", "skills")
    if tuple(skills_root.parts[-3:]) != expected_suffix:
        raise P0RuntimeCompositionError(
            "engineering skill root must use tools/software-factory/skills"
        )
    repository_root = skills_root.parents[2]
    if not repository_root.is_dir():
        raise P0RuntimeCompositionError(
            "repository root derived from engineering skills is unavailable"
        )
    return repository_root
