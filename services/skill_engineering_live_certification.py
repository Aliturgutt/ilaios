"""Live zero-cost provider certification for runtime-admitted Skill Engineering skills.

This harness executes the five explicitly admitted first-party Skill Engineering
packages through the existing NamedAgentExecutor -> GovernedRuntime -> governed
AI provider adapter path. It creates no second runtime, registry, router, policy,
or verifier authority. Each producer route is independently verified against
persisted runtime evidence before the receipt can become VERIFIED.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.ai_governance import Scope, ScopeKind
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import (
    IndependentVerifierExecutor,
    ProducerEvidence,
)
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.p0_ai_provider_config import (
    P0AIProviderConfiguration,
    load_p0_ai_provider_configuration,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.skill_engineering_runtime import SKILL_ENGINEERING_RUNTIME_BINDINGS
from services.software_factory_skills import default_skills_root


class SkillEngineeringLiveCertificationError(RuntimeError):
    """Live Skill Engineering provider certification failed closed."""


_INPUT_TOKEN_RESERVATION = 1024
_OUTPUT_TOKEN_RESERVATION = 1024


def run_skill_engineering_live_certification(
    *,
    repository_root: Path,
    output_dir: Path,
    revision_sha: str,
    configuration: P0AIProviderConfiguration | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise SkillEngineeringLiveCertificationError("repository root is unavailable")
    if len(revision_sha) != 40 or any(
        ch not in "0123456789abcdef" for ch in revision_sha
    ):
        raise SkillEngineeringLiveCertificationError(
            "revision SHA must be lowercase git SHA-1"
        )
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise SkillEngineeringLiveCertificationError(
            "certification timestamp must be aware"
        )

    config = configuration or discover_free_openrouter_agent_configuration()
    if config is None:
        raise SkillEngineeringLiveCertificationError(
            "governed provider configuration is unavailable"
        )

    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    database = output / "skill-engineering-runtime.sqlite3"
    migrate_database(database)

    external_adapters = dict(SecurityAgentRuntimeAdapters().runtime_adapters())
    external_adapters.update(config.adapter.runtime_adapters())
    runtime = GovernedRuntime(database, external_adapters=external_adapters)
    grants = GrantPolicy()
    composition = compose_p0_runtime(
        runtime,
        grants,
        engineering_skills_root=default_skills_root(root),
        ai_adapter=config.adapter,
        ai_provider_capabilities=config.provider_capabilities,
    )
    named = composition.named_executor
    verifier = IndependentVerifierExecutor(named, config.adapter)

    tenant_id = "ilaios-skill-engineering-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)
    receipts: list[dict[str, object]] = []

    for index, binding in enumerate(SKILL_ENGINEERING_RUNTIME_BINDINGS):
        selection = config.adapter.select(binding.capability)
        invocation = AgentInvocation(
            invocation_id=f"skill-engineering-live-{index}-{binding.skill_id}",
            caller_id="ilaios.agent.core.orchestrator.v1",
            target_id=binding.owner_agent_id,
            capability=binding.capability,
            permission=binding.permission,
            input_class="governed_task",
            requested_output_class="proposal",
            prompt=(
                f"ILAIOS live certification for {binding.skill_id}. "
                "Return one concise bounded proposal only. Do not claim deployment, "
                "external side effects, promotion, or production verification."
            ),
            contains_secret=False,
            external_egress=True,
            dlp_approved=True,
            security_scan_passed=True,
        )
        producer = named.execute(
            invocation,
            _grant(binding.owner_agent_id, binding.permission, observed_at, index),
            skill_id=binding.skill_id,
            payload={
                "request_id": invocation.invocation_id,
                "tenant_id": tenant_id,
                "model_id": selection.model_id,
                "prompt": invocation.prompt,
                "input_tokens": _INPUT_TOKEN_RESERVATION,
                "max_output_tokens": _OUTPUT_TOKEN_RESERVATION,
                "scopes": [
                    {"kind": scope.kind.value, "scope_id": scope.scope_id}
                    for scope in scopes
                ],
                "now": observed_at.isoformat(),
            },
            now=observed_at,
            preferred_provider_id=selection.provider_id,
        )
        producer_digest = execution_evidence_digest(producer)
        verification = verifier.verify(
            ProducerEvidence(producer, producer_digest),
            _grant(
                INDEPENDENT_VERIFIER_ID,
                "evidence.read",
                observed_at,
                1000 + index,
            ),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
        )
        if not verification.passed:
            raise SkillEngineeringLiveCertificationError(
                f"IndependentVerifier rejected {binding.skill_id}"
            )
        route_output = producer.route.get("output")
        if not isinstance(route_output, dict):
            raise SkillEngineeringLiveCertificationError(
                "provider output evidence is missing"
            )
        if route_output.get("provider_id") != selection.provider_id:
            raise SkillEngineeringLiveCertificationError("provider identity drifted")
        if route_output.get("model_id") != selection.model_id:
            raise SkillEngineeringLiveCertificationError("model identity drifted")
        if route_output.get("skill_id") != binding.skill_id:
            raise SkillEngineeringLiveCertificationError("skill identity drifted")
        if route_output.get("actual_cost_usd") != "0":
            raise SkillEngineeringLiveCertificationError(
                "zero-cost certification observed cost"
            )

        receipts.append(
            {
                "skill_id": binding.skill_id,
                "logical_id": binding.logical_id,
                "agent_id": binding.owner_agent_id,
                "capability": binding.capability,
                "permission": binding.permission,
                "provider_id": selection.provider_id,
                "model_id": selection.model_id,
                "skill_sha256": route_output.get("skill_sha256"),
                "producer_evidence_sha256": producer_digest,
                "verifier_evidence_sha256": verification.verifier_evidence_digest,
                "actual_cost_usd": route_output.get("actual_cost_usd"),
                "response_id": route_output.get("response_id"),
            }
        )

    expected_ids = [binding.skill_id for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS]
    observed_ids = [str(item["skill_id"]) for item in receipts]
    if observed_ids != expected_ids or len(receipts) != 5:
        raise SkillEngineeringLiveCertificationError(
            "5-of-5 runtime coverage was not proven"
        )
    provider_ids = sorted({str(item["provider_id"]) for item in receipts})
    if not provider_ids:
        raise SkillEngineeringLiveCertificationError(
            "certification provider evidence is missing"
        )

    receipt: dict[str, object] = {
        "status": "VERIFIED",
        "revision_sha": revision_sha,
        "verified_skill_count": len(receipts),
        "target_skill_count": len(expected_ids),
        "zero_cost_only": True,
        "zero_cost_openrouter_only": provider_ids == ["openrouter"],
        "provider_ids": provider_ids,
        "skills": receipts,
        "completed_at": observed_at.isoformat(),
    }
    (output / "skill-engineering-live-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def _grant(
    subject_id: str,
    permission: str,
    now: datetime,
    index: int,
) -> ExecutionGrant:
    return ExecutionGrant(
        grant_id=f"skill-engineering-live-grant-{index}",
        subject_id=subject_id,
        actions=frozenset({permission}),
        resources=frozenset({subject_id}),
        expires_at=now + timedelta(minutes=10),
        budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def _configuration_from_environment() -> P0AIProviderConfiguration | None:
    mode = os.environ.get("SKILL_ENGINEERING_CERT_PROVIDER_MODE", "openrouter").strip()
    if mode == "openrouter":
        return discover_free_openrouter_agent_configuration()
    if mode == "configured":
        return load_p0_ai_provider_configuration()
    raise SkillEngineeringLiveCertificationError(
        "unknown Skill Engineering certification provider mode"
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    revision = os.environ.get("GITHUB_SHA", "").strip().lower()
    proof_dir = Path(
        os.environ.get(
            "SKILL_ENGINEERING_PROOF_DIR",
            "artifacts/skill-engineering-live-proof",
        )
    )
    receipt = run_skill_engineering_live_certification(
        repository_root=root,
        output_dir=proof_dir,
        revision_sha=revision,
        configuration=_configuration_from_environment(),
    )
    raw_provider_ids = receipt.get("provider_ids")
    if not isinstance(raw_provider_ids, list):
        raise SkillEngineeringLiveCertificationError(
            "certification provider list is malformed"
        )
    provider_ids: list[str] = []
    for provider_id in raw_provider_ids:
        if not isinstance(provider_id, str):
            raise SkillEngineeringLiveCertificationError(
                "certification provider identity is malformed"
            )
        provider_ids.append(provider_id)
    print(
        "SKILL_ENGINEERING_LIVE_CERTIFICATION=PASS "
        f"verified={receipt['verified_skill_count']}/{receipt['target_skill_count']} "
        f"providers={','.join(provider_ids)}"
    )


if __name__ == "__main__":
    main()
