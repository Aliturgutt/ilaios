"""Deterministic IndependentVerifier execution over persisted canonical evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from services.agent_governance import AgentInvocation
from services.agent_registry import (
    INDEPENDENT_VERIFIER_ID,
    SECURITY_VERIFIER_ID,
    SUPERVISOR_ID,
)
from services.independent_verifier_execution import (
    IndependentVerifierExecutionError,
    IndependentVerifierResult,
    ProducerEvidence,
)
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.p0_skill_catalog import INDEPENDENT_VERIFIER_SKILL
from services.runtime import ExecutionGrant, GovernedRuntime
from services.runtime.independent_verifier_adapter import (
    INDEPENDENT_VERIFIER_PROVIDER_ID,
)


class StructuralIndependentVerifier:
    """Verify producer route/digest integrity, then persist verifier execution."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        runtime: GovernedRuntime,
    ) -> None:
        self._named = named_executor
        self._runtime = runtime

    def verify(
        self,
        producer: ProducerEvidence,
        grant: ExecutionGrant,
        *,
        now: datetime,
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

        persisted = self._persisted_route(execution)
        recomputed_digest = _producer_execution_digest(execution)
        execution_route_digest = _route_sha256(execution.route)
        persisted_route_digest = _route_sha256(persisted)

        caller_id = (
            SECURITY_VERIFIER_ID if producer_id == SECURITY_VERIFIER_ID else SUPERVISOR_ID
        )
        prompt = json.dumps(
            {
                "producer_agent_id": producer_id,
                "producer_evidence_digest": producer.evidence_digest,
                "verification_mode": "deterministic-structural-evidence",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        invocation = AgentInvocation(
            invocation_id=f"structural-verify:{producer.evidence_digest[:24]}",
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
            payload={
                "producer_agent_id": producer_id,
                "producer_evidence_digest": producer.evidence_digest,
                "recomputed_evidence_digest": recomputed_digest,
                "persisted_route_sha256": persisted_route_digest,
                "execution_route_sha256": execution_route_digest,
            },
            now=now,
            preferred_provider_id=INDEPENDENT_VERIFIER_PROVIDER_ID,
        )
        verdict, findings = _parse_structural_verdict(
            verifier, producer.evidence_digest
        )
        return IndependentVerifierResult(
            producer_agent_id=producer_id,
            verifier_execution=verifier,
            producer_evidence_digest=producer.evidence_digest,
            verifier_evidence_digest=_verifier_route_digest(verifier),
            passed=verdict == "PASS",
            findings=findings,
            model_id="deterministic-structural-v1",
            provider_id=INDEPENDENT_VERIFIER_PROVIDER_ID,
        )

    def _persisted_route(self, execution: NamedAgentExecution) -> dict[str, object]:
        sequence = execution.route.get("sequence")
        if not isinstance(sequence, int):
            raise IndependentVerifierExecutionError("producer route sequence is missing")
        candidates = [
            route for route in self._runtime.routes() if route.get("sequence") == sequence
        ]
        if len(candidates) != 1:
            raise IndependentVerifierExecutionError(
                "producer persisted route cannot be uniquely resolved"
            )
        persisted = candidates[0]
        if persisted != execution.route:
            raise IndependentVerifierExecutionError(
                "producer execution diverges from persisted runtime route"
            )
        return persisted


def _producer_execution_digest(execution: NamedAgentExecution) -> str:
    material = {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "route_sequence": execution.route.get("sequence"),
        "skill_id": execution.route.get("skill_id"),
        "provider_id": execution.route.get("provider_id"),
        "capability": execution.route.get("capability"),
        "output": execution.route.get("output"),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _route_sha256(route: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(route, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _parse_structural_verdict(
    execution: NamedAgentExecution,
    producer_digest: str,
) -> tuple[str, tuple[str, ...]]:
    output = execution.route.get("output")
    if not isinstance(output, dict):
        raise IndependentVerifierExecutionError("structural verifier output is missing")
    if output.get("structural_verification") is not True:
        raise IndependentVerifierExecutionError("structural verifier identity is missing")
    verdict = output.get("verdict")
    digest = output.get("producer_evidence_digest")
    findings = output.get("findings")
    if verdict not in {"PASS", "FAIL"}:
        raise IndependentVerifierExecutionError("structural verifier verdict is invalid")
    if digest != producer_digest:
        raise IndependentVerifierExecutionError(
            "structural verifier did not attest exact producer evidence"
        )
    if not isinstance(findings, list) or not all(
        isinstance(item, str) and item.strip() for item in findings
    ):
        raise IndependentVerifierExecutionError("structural findings are invalid")
    if verdict == "PASS" and findings:
        raise IndependentVerifierExecutionError("PASS cannot contain findings")
    if verdict == "FAIL" and not findings:
        raise IndependentVerifierExecutionError("FAIL requires findings")
    return verdict, tuple(item.strip() for item in findings)


def _verifier_route_digest(execution: NamedAgentExecution) -> str:
    material = {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "sequence": execution.route.get("sequence"),
        "skill_id": execution.route.get("skill_id"),
        "provider_id": execution.route.get("provider_id"),
        "capability": execution.route.get("capability"),
        "output": execution.route.get("output"),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
