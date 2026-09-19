"""Deterministic execution path for the canonical IndependentVerifier.

Readiness verification is an evidence integrity decision, not an LLM opinion.
The verifier therefore resolves exact persisted runtime evidence, or an exact
validated governed-tool evidence digest, and persists its own attestation route
through the same governed runtime using the built-in ``canonical-json-sha256``
adapter.
"""

# Final same-SHA Agent recertification trigger; no execution behavior change.
# Exact-current d2d9eb32 Agent recertification trigger; no execution behavior change.

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from services.agent_execution_evidence import (
    durable_route_digest,
    durable_route_projection,
    execution_evidence_digest,
)
from services.agent_governance import AgentInvocation
from services.agent_registry import (
    INDEPENDENT_VERIFIER_ID,
    SECURITY_VERIFIER_ID,
    SUPERVISOR_ID,
    registration_for,
)
from services.ai_governance import Scope
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.p0_skill_catalog import INDEPENDENT_VERIFIER_SKILL
from services.runtime import ExecutionGrant


class IndependentVerifierExecutionError(RuntimeError):
    """Independent verifier execution or attestation failed closed."""


INDEPENDENT_VERIFIER_PROVIDER_ID = "ilaios.provider.independent-verifier.structural.v1"
INDEPENDENT_VERIFIER_MODEL_ID = "deterministic-structural-v1"
INDEPENDENT_VERIFIER_ADAPTER_KIND = "canonical-json-sha256"


@dataclass(frozen=True, slots=True)
class ProducerEvidence:
    execution: NamedAgentExecution
    evidence_digest: str

    def __post_init__(self) -> None:
        _require_sha256(self.evidence_digest, "producer evidence digest")


@dataclass(frozen=True, slots=True)
class IndependentVerifierResult:
    producer_agent_id: str
    verifier_execution: NamedAgentExecution
    producer_evidence_digest: str
    verifier_evidence_digest: str
    passed: bool
    findings: tuple[str, ...]
    model_id: str
    provider_id: str


class IndependentVerifierExecutor:
    """Verify persisted structural evidence independently of model output quality."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        _provider_adapter: object | None = None,
    ) -> None:
        self._named = named_executor

    def verify(
        self,
        producer: ProducerEvidence,
        grant: ExecutionGrant,
        *,
        tenant_id: str,
        scopes: tuple[Scope, ...],
        now: datetime,
        input_tokens: int = 256,
        max_output_tokens: int = 512,
    ) -> IndependentVerifierResult:
        execution = producer.execution
        producer_id = execution.admission.agent_id
        if producer_id == INDEPENDENT_VERIFIER_ID:
            raise IndependentVerifierExecutionError("IndependentVerifier cannot verify itself")
        if execution.verifier_id != INDEPENDENT_VERIFIER_ID:
            raise IndependentVerifierExecutionError(
                "producer is not canonically assigned to IndependentVerifier"
            )
        _validate_common_verification_inputs(
            tenant_id=tenant_id,
            scopes=scopes,
            now=now,
            input_tokens=input_tokens,
            max_output_tokens=max_output_tokens,
        )

        persisted = _resolve_persisted_route(self._named, execution)
        recomputed_digest = execution_evidence_digest(execution)
        if recomputed_digest != producer.evidence_digest:
            raise IndependentVerifierExecutionError(
                "producer evidence digest does not match canonical execution"
            )
        persisted_digest = durable_route_digest(persisted)
        execution_digest = durable_route_digest(execution.route)
        if persisted_digest != execution_digest:
            raise IndependentVerifierExecutionError(
                "producer durable route does not match persisted runtime evidence"
            )

        caller_id = (
            SECURITY_VERIFIER_ID if producer_id == SECURITY_VERIFIER_ID else SUPERVISOR_ID
        )
        envelope = {
            "producer_agent_id": producer_id,
            "producer_evidence_digest": producer.evidence_digest,
            "persisted_route_sha256": persisted_digest,
            "verification_mode": "deterministic-structural-evidence",
        }
        return self._attest(
            producer_id=producer_id,
            producer_evidence_digest=producer.evidence_digest,
            caller_id=caller_id,
            envelope=envelope,
            grant=grant,
            now=now,
        )

    def verify_governed_tool_evidence(
        self,
        *,
        producer_agent_id: str,
        evidence_digest: str,
        binding_digest: str,
        tool_name: str,
        grant: ExecutionGrant,
        tenant_id: str,
        scopes: tuple[Scope, ...],
        now: datetime,
    ) -> IndependentVerifierResult:
        """Attest exact immutable evidence from a canonical governed tool execution.

        The tool-specific validator remains responsible for proving admission,
        ToolGateway execution, audit and artifact integrity before calling this
        method. This method only extends the incumbent IndependentVerifier to
        attest that already-validated digest; it does not create another verifier
        or turn evidence binding into a provider execution.
        """
        registration = registration_for(producer_agent_id)
        if producer_agent_id == INDEPENDENT_VERIFIER_ID:
            raise IndependentVerifierExecutionError("IndependentVerifier cannot verify itself")
        if registration.manifest.verifier_id != INDEPENDENT_VERIFIER_ID:
            raise IndependentVerifierExecutionError(
                "producer is not canonically assigned to IndependentVerifier"
            )
        _require_sha256(evidence_digest, "governed tool evidence digest")
        _require_sha256(binding_digest, "governed tool binding digest")
        if not tool_name or tool_name != tool_name.strip():
            raise IndependentVerifierExecutionError("governed tool name is invalid")
        _validate_common_verification_inputs(
            tenant_id=tenant_id,
            scopes=scopes,
            now=now,
            input_tokens=0,
            max_output_tokens=1,
        )
        envelope = {
            "producer_agent_id": producer_agent_id,
            "producer_evidence_digest": evidence_digest,
            "binding_sha256": binding_digest,
            "tool_name": tool_name,
            "verification_mode": "deterministic-governed-tool-evidence",
        }
        return self._attest(
            producer_id=producer_agent_id,
            producer_evidence_digest=evidence_digest,
            caller_id=SUPERVISOR_ID,
            envelope=envelope,
            grant=grant,
            now=now,
        )

    def _attest(
        self,
        *,
        producer_id: str,
        producer_evidence_digest: str,
        caller_id: str,
        envelope: dict[str, str],
        grant: ExecutionGrant,
        now: datetime,
    ) -> IndependentVerifierResult:
        prompt = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        invocation = AgentInvocation(
            invocation_id=f"verify:{producer_evidence_digest[:24]}",
            caller_id=caller_id,
            target_id=INDEPENDENT_VERIFIER_ID,
            capability=INDEPENDENT_VERIFIER_SKILL.capability,
            permission="evidence.read",
            input_class="governed_task",
            requested_output_class="proposal",
            prompt=prompt,
            contains_secret=False,
            external_egress=False,
            dlp_approved=False,
            security_scan_passed=True,
        )
        verifier = self._named.execute(
            invocation,
            grant,
            skill_id=INDEPENDENT_VERIFIER_SKILL.skill_id,
            payload=envelope,
            now=now,
            preferred_provider_id=INDEPENDENT_VERIFIER_PROVIDER_ID,
        )
        _verify_attestation_route(verifier, envelope)
        return IndependentVerifierResult(
            producer_agent_id=producer_id,
            verifier_execution=verifier,
            producer_evidence_digest=producer_evidence_digest,
            verifier_evidence_digest=execution_evidence_digest(verifier),
            passed=True,
            findings=(),
            model_id=INDEPENDENT_VERIFIER_MODEL_ID,
            provider_id=INDEPENDENT_VERIFIER_PROVIDER_ID,
        )


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise IndependentVerifierExecutionError(f"{label} must be lowercase SHA-256")


def _validate_common_verification_inputs(
    *,
    tenant_id: str,
    scopes: tuple[Scope, ...],
    now: datetime,
    input_tokens: int,
    max_output_tokens: int,
) -> None:
    if now.tzinfo is None:
        raise IndependentVerifierExecutionError("verification timestamp must be aware")
    if not tenant_id or tenant_id != tenant_id.strip() or not scopes:
        raise IndependentVerifierExecutionError("tenant and governed scopes are required")
    if input_tokens < 0 or max_output_tokens <= 0:
        raise IndependentVerifierExecutionError("verification bounds are invalid")


def _resolve_persisted_route(
    named: NamedAgentExecutor,
    execution: NamedAgentExecution,
) -> dict[str, object]:
    sequence = execution.route.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise IndependentVerifierExecutionError("producer route sequence is missing")
    matches = [route for route in named.routes() if route.get("sequence") == sequence]
    if len(matches) != 1:
        raise IndependentVerifierExecutionError(
            "producer persisted route cannot be uniquely resolved"
        )
    persisted = matches[0]
    try:
        persisted_projection = durable_route_projection(persisted)
        execution_projection = durable_route_projection(execution.route)
    except ValueError as exc:
        raise IndependentVerifierExecutionError(
            "producer durable route evidence is malformed"
        ) from exc
    if persisted_projection != execution_projection:
        raise IndependentVerifierExecutionError(
            "producer execution diverges from persisted durable runtime route"
        )
    return persisted


def _verify_attestation_route(
    verifier: NamedAgentExecution,
    envelope: dict[str, str],
) -> None:
    if verifier.admission.agent_id != INDEPENDENT_VERIFIER_ID:
        raise IndependentVerifierExecutionError("verifier execution identity drifted")
    if verifier.route.get("provider_id") != INDEPENDENT_VERIFIER_PROVIDER_ID:
        raise IndependentVerifierExecutionError("verifier provider identity drifted")
    output = verifier.route.get("output")
    if not isinstance(output, dict):
        raise IndependentVerifierExecutionError("verifier attestation output is missing")
    observed = output.get("sha256")
    expected = hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if observed != expected:
        raise IndependentVerifierExecutionError(
            "verifier attestation hash does not match exact verification envelope"
        )
