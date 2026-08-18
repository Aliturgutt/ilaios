"""Provider-backed execution path for the canonical IndependentVerifier."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.agent_governance import AgentInvocation
from services.agent_registry import INDEPENDENT_VERIFIER_ID, SECURITY_VERIFIER_ID, SUPERVISOR_ID
from services.ai_governance import GovernanceError, Scope
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.p0_skill_catalog import INDEPENDENT_VERIFIER_SKILL
from services.runtime import ExecutionGrant
from services.runtime.ai_provider_adapter import AIProviderError, GovernedAIProviderAdapter
from services.runtime.routing import RuntimeError as RuntimeRoutingError


class IndependentVerifierExecutionError(RuntimeError):
    """Independent verifier execution or attestation failed closed."""


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
    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        self._named = named_executor
        self._providers = provider_adapter

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
        if execution.verifier_id != INDEPENDENT_VERIFIER_ID:
            raise IndependentVerifierExecutionError(
                "producer is not canonically assigned to IndependentVerifier"
            )
        if now.tzinfo is None:
            raise IndependentVerifierExecutionError("verification timestamp must be aware")
        if not tenant_id or tenant_id != tenant_id.strip() or not scopes:
            raise IndependentVerifierExecutionError("tenant and governed scopes are required")
        if input_tokens < 0 or max_output_tokens <= 0:
            raise IndependentVerifierExecutionError("verification token bounds are invalid")

        caller_id = SECURITY_VERIFIER_ID if producer_id == SECURITY_VERIFIER_ID else SUPERVISOR_ID
        envelope = _evidence_envelope(producer)
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
            external_egress=True,
            dlp_approved=True,
            security_scan_passed=True,
        )

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    INDEPENDENT_VERIFIER_SKILL.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                raise IndependentVerifierExecutionError(
                    "no governed IndependentVerifier provider remains"
                ) from (last_error or exc)
            payload = {
                "request_id": invocation.invocation_id,
                "tenant_id": tenant_id,
                "model_id": selection.model_id,
                "prompt": prompt,
                "input_tokens": input_tokens,
                "max_output_tokens": max_output_tokens,
                "scopes": [
                    {"kind": scope.kind.value, "scope_id": scope.scope_id}
                    for scope in scopes
                ],
                "now": now.isoformat(),
            }
            try:
                verifier = self._named.execute(
                    invocation,
                    grant,
                    skill_id=INDEPENDENT_VERIFIER_SKILL.skill_id,
                    payload=payload,
                    now=now,
                    preferred_provider_id=selection.provider_id,
                )
            except (AIProviderError, GovernanceError, RuntimeRoutingError) as exc:
                denied_models.add(selection.model_id)
                last_error = exc
                continue

            verdict, findings = _parse_verdict(
                verifier.route.get("output"), producer.evidence_digest
            )
            return IndependentVerifierResult(
                producer_agent_id=producer_id,
                verifier_execution=verifier,
                producer_evidence_digest=producer.evidence_digest,
                verifier_evidence_digest=_route_digest(verifier),
                passed=verdict == "PASS",
                findings=findings,
                model_id=selection.model_id,
                provider_id=selection.provider_id,
            )


def _evidence_envelope(producer: ProducerEvidence) -> dict[str, object]:
    execution = producer.execution
    output = execution.route.get("output")
    output_hash = hashlib.sha256(
        json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return {
        "producer_agent_id": execution.admission.agent_id,
        "producer_verifier_id": execution.admission.verifier_id,
        "producer_evidence_digest": producer.evidence_digest,
        "producer_invocation_id": execution.admission.invocation_id,
        "producer_route_sequence": execution.route.get("sequence"),
        "producer_skill_id": execution.route.get("skill_id"),
        "producer_provider_id": execution.route.get("provider_id"),
        "producer_capability": execution.route.get("capability"),
        "producer_output_sha256": output_hash,
        "required_response": {
            "verdict": "PASS|FAIL",
            "producer_evidence_digest": producer.evidence_digest,
            "findings": ["string"],
        },
    }


def _parse_verdict(output: object, producer_digest: str) -> tuple[str, tuple[str, ...]]:
    if not isinstance(output, dict):
        raise IndependentVerifierExecutionError("verifier runtime output is missing")
    raw = output.get("text")
    if not isinstance(raw, str) or not raw.strip():
        raise IndependentVerifierExecutionError("verifier returned no verdict")
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IndependentVerifierExecutionError("verifier verdict must be strict JSON") from exc
    if not isinstance(document, dict) or set(document) != {
        "verdict", "producer_evidence_digest", "findings"
    }:
        raise IndependentVerifierExecutionError("verifier verdict contract is invalid")
    verdict = document.get("verdict")
    if verdict not in {"PASS", "FAIL"}:
        raise IndependentVerifierExecutionError("verifier verdict must be PASS or FAIL")
    if document.get("producer_evidence_digest") != producer_digest:
        raise IndependentVerifierExecutionError("verifier did not attest exact producer evidence")
    findings = document.get("findings")
    if not isinstance(findings, list) or not all(
        isinstance(item, str) and item.strip() for item in findings
    ):
        raise IndependentVerifierExecutionError("verifier findings must be strings")
    normalized = tuple(item.strip() for item in findings)
    if verdict == "PASS" and normalized:
        raise IndependentVerifierExecutionError("PASS verdict cannot retain unresolved findings")
    if verdict == "FAIL" and not normalized:
        raise IndependentVerifierExecutionError("FAIL verdict requires findings")
    return verdict, normalized


def _route_digest(execution: NamedAgentExecution) -> str:
    material: dict[str, Any] = {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "route": execution.route,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
