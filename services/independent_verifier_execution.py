"""Deterministic execution path for the canonical IndependentVerifier.

Readiness verification is an evidence integrity decision, not an LLM opinion.
The verifier therefore resolves the exact producer route from the canonical
runtime database, recomputes the canonical execution evidence digest, and
persists its own attestation route through the same governed runtime using the
built-in ``canonical-json-sha256`` adapter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_registry import (
    INDEPENDENT_VERIFIER_ID,
    SECURITY_VERIFIER_ID,
    SUPERVISOR_ID,
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
        if len(self.evidence_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.evidence_digest
        ):
            raise IndependentVerifierExecutionError(
                "producer evidence digest must be lowercase SHA-256"
            )


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
        if now.tzinfo is None:
            raise IndependentVerifierExecutionError("verification timestamp must be aware")
        if not tenant_id or tenant_id != tenant_id.strip() or not scopes:
            raise IndependentVerifierExecutionError("tenant and governed scopes are required")
        if input_tokens < 0 or max_output_tokens <= 0:
            raise IndependentVerifierExecutionError("verification bounds are invalid")

        persisted = _resolve_persisted_route(self._named, execution)
        recomputed_digest = execution_evidence_digest(execution)
        if recomputed_digest != producer.evidence_digest:
            raise IndependentVerifierExecutionError(
                "producer evidence digest does not match canonical execution"
            )
        persisted_digest = _canonical_route_digest(persisted)
        execution_digest = _canonical_route_digest(execution.route)
        if persisted_digest != execution_digest:
            raise IndependentVerifierExecutionError(
                "producer persisted route does not match execution evidence"
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
        prompt = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        invocation = AgentInvocation(
            invocation_id=f"verify:{producer.evidence_digest[:24]}",
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
            producer_evidence_digest=producer.evidence_digest,
            verifier_evidence_digest=execution_evidence_digest(verifier),
            passed=True,
            findings=(),
            model_id=INDEPENDENT_VERIFIER_MODEL_ID,
            provider_id=INDEPENDENT_VERIFIER_PROVIDER_ID,
        )


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
    if _comparable_route(persisted) != _comparable_route(execution.route):
        raise IndependentVerifierExecutionError(
            "producer execution diverges from persisted runtime route"
        )
    return persisted


def _comparable_route(route: dict[str, object]) -> dict[str, object]:
    """Project fields present in both runtime return and persisted route records."""
    sequence = route.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise IndependentVerifierExecutionError("persisted route sequence is invalid")
    projected: dict[str, object] = {"sequence": sequence}
    for field in ("agent_id", "skill_id", "provider_id", "capability"):
        value = route.get(field)
        if not isinstance(value, str) or not value or value != value.strip():
            raise IndependentVerifierExecutionError(
                f"persisted route {field} is invalid"
            )
        projected[field] = value
    output = route.get("output")
    if not isinstance(output, dict):
        raise IndependentVerifierExecutionError("persisted route output is invalid")
    projected["output"] = output
    return projected


def _canonical_route_digest(route: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            _comparable_route(route),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


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
