"""Governed execution wrapper for P0 defensive Security agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_registry import SECURITY_VERIFIER_ID
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.p0_agent_execution import binding_for
from services.runtime import ExecutionGrant
from services.runtime.security_agent_adapters import SECURITY_LOCAL_PROVIDERS
from services.security_methodology_skills import definition_for


class SecurityAgentExecutionError(RuntimeError):
    """Defensive security execution violated its canonical scope or verifier path."""


_SECURITY_PROVIDER_BY_AGENT = {
    "ilaios.agent.security.codesec.v1": "ilaios.security.local.codesec",
    "ilaios.agent.security.web-api.v1": "ilaios.security.local.web-api",
    "ilaios.agent.security.supply-chain.v1": "ilaios.security.local.supply-chain",
    "ilaios.agent.security.infrastructure.v1": "ilaios.security.local.infrastructure",
    SECURITY_VERIFIER_ID: "ilaios.security.local.verifier",
}


@dataclass(frozen=True, slots=True)
class SecurityVerificationResult:
    producer: NamedAgentExecution
    verifier: NamedAgentExecution
    producer_evidence_digest: str
    verifier_evidence_digest: str
    passed: bool


class DefensiveSecurityAgentExecutor:
    def __init__(self, named_executor: NamedAgentExecutor) -> None:
        self._named = named_executor

    def execute_specialist(
        self,
        invocation: AgentInvocation,
        grant: ExecutionGrant,
        *,
        skill_id: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> NamedAgentExecution:
        binding = binding_for(invocation.target_id)
        if binding.execution_mode != "defensive-local":
            raise SecurityAgentExecutionError(
                "only defensive-local specialist bindings are accepted"
            )
        if invocation.capability != binding.capability:
            raise SecurityAgentExecutionError(
                "security capability diverges from binding"
            )
        if invocation.permission != binding.permission:
            raise SecurityAgentExecutionError(
                "security permission diverges from binding"
            )

        supplementary = definition_for(skill_id)
        if supplementary is None:
            if skill_id != binding.primary_skill_id:
                raise SecurityAgentExecutionError(
                    "security skill is outside canonical binding"
                )
        elif (
            supplementary.owner_agent_id != invocation.target_id
            or supplementary.capability != invocation.capability
        ):
            raise SecurityAgentExecutionError(
                "security methodology skill owner or capability mismatch"
            )

        provider_id = _SECURITY_PROVIDER_BY_AGENT.get(invocation.target_id)
        if provider_id is None:
            raise SecurityAgentExecutionError(
                "security specialist provider is unavailable"
            )
        return self._named.execute(
            invocation,
            grant,
            skill_id=skill_id,
            payload=payload,
            now=now,
            preferred_provider_id=provider_id,
        )

    def independently_verify(
        self,
        producer: NamedAgentExecution,
        verifier_invocation: AgentInvocation,
        verifier_grant: ExecutionGrant,
        *,
        skill_id: str,
        now: datetime,
    ) -> SecurityVerificationResult:
        if producer.admission.agent_id == SECURITY_VERIFIER_ID:
            raise SecurityAgentExecutionError(
                "SecurityVerifier cannot verify itself"
            )
        if producer.verifier_id != SECURITY_VERIFIER_ID:
            raise SecurityAgentExecutionError(
                "producer is not canonically assigned to SecurityVerifier"
            )
        if verifier_invocation.target_id != SECURITY_VERIFIER_ID:
            raise SecurityAgentExecutionError(
                "verification target must be SecurityVerifier"
            )
        binding = binding_for(SECURITY_VERIFIER_ID)
        if skill_id != binding.primary_skill_id:
            raise SecurityAgentExecutionError(
                "verification must use the canonical SecurityVerifier skill"
            )
        if verifier_invocation.capability != binding.capability:
            raise SecurityAgentExecutionError(
                "verifier capability diverges from binding"
            )
        if verifier_invocation.permission != binding.permission:
            raise SecurityAgentExecutionError(
                "verifier permission diverges from binding"
            )

        report = producer.route.get("output")
        if not isinstance(report, dict):
            raise SecurityAgentExecutionError(
                "producer persisted report is missing"
            )
        producer_digest = execution_evidence_digest(producer)
        verifier = self._named.execute(
            verifier_invocation,
            verifier_grant,
            skill_id=skill_id,
            payload={
                "producer_id": producer.admission.agent_id,
                "verifier_id": SECURITY_VERIFIER_ID,
                "producer_evidence_digest": producer_digest,
                "report": report,
            },
            now=now,
            preferred_provider_id="ilaios.security.local.verifier",
        )
        output = verifier.route.get("output")
        if not isinstance(output, dict) or not isinstance(
            output.get("verified"), bool
        ):
            raise SecurityAgentExecutionError(
                "SecurityVerifier output is incomplete"
            )
        if output.get("producer_id") != producer.admission.agent_id:
            raise SecurityAgentExecutionError(
                "verifier producer identity mismatch"
            )
        if output.get("verifier_id") != SECURITY_VERIFIER_ID:
            raise SecurityAgentExecutionError(
                "verifier identity mismatch"
            )
        return SecurityVerificationResult(
            producer=producer,
            verifier=verifier,
            producer_evidence_digest=producer_digest,
            verifier_evidence_digest=execution_evidence_digest(verifier),
            passed=bool(output["verified"]),
        )


def security_local_provider_specs() -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (provider_id, adapter_kind, capability)
        for provider_id, (adapter_kind, capability) in sorted(
            SECURITY_LOCAL_PROVIDERS.items()
        )
    )
