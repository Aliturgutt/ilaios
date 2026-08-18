"""Independent verifier contract for evidence-gated agent readiness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from services.named_agent_executor import NamedAgentExecution
from services.p0_agent_execution import ProviderBackedAgentResult


class AgentVerificationError(ValueError):
    """Independent verification evidence is incomplete or contradictory."""


@dataclass(frozen=True, slots=True)
class IndependentVerificationVerdict:
    producer_agent_id: str
    verifier_agent_id: str
    producer_evidence_digest: str
    verifier_route_digest: str
    passed: bool
    findings: tuple[str, ...]


def compile_independent_verification(
    producer: ProviderBackedAgentResult,
    verifier: NamedAgentExecution,
) -> IndependentVerificationVerdict:
    producer_agent_id = producer.execution.admission.agent_id
    verifier_agent_id = verifier.admission.agent_id
    if verifier_agent_id == producer_agent_id:
        raise AgentVerificationError("producer cannot independently verify itself")
    if producer.execution.verifier_id != verifier_agent_id:
        raise AgentVerificationError("verifier identity does not match producer manifest")

    output = verifier.route.get("output")
    if not isinstance(output, dict):
        raise AgentVerificationError("verifier route output is missing")
    raw_text = output.get("text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise AgentVerificationError("verifier must return a strict verdict document")
    try:
        document = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AgentVerificationError("verifier verdict must be strict JSON") from exc
    if not isinstance(document, dict) or set(document) != {
        "verdict", "producer_evidence_digest", "findings"
    }:
        raise AgentVerificationError("verifier verdict contract is invalid")
    verdict = document.get("verdict")
    evidence_digest = document.get("producer_evidence_digest")
    findings = document.get("findings")
    if verdict not in {"PASS", "FAIL"}:
        raise AgentVerificationError("verifier verdict must be PASS or FAIL")
    if evidence_digest != producer.evidence_digest:
        raise AgentVerificationError("verifier did not attest the exact producer evidence")
    if not isinstance(findings, list) or not all(
        isinstance(item, str) and item.strip() for item in findings
    ):
        raise AgentVerificationError("verifier findings must be a string list")
    if verdict == "PASS" and findings:
        raise AgentVerificationError("PASS verdict cannot contain unresolved findings")
    if verdict == "FAIL" and not findings:
        raise AgentVerificationError("FAIL verdict requires at least one finding")
    return IndependentVerificationVerdict(
        producer_agent_id=producer_agent_id,
        verifier_agent_id=verifier_agent_id,
        producer_evidence_digest=producer.evidence_digest,
        verifier_route_digest=_route_digest(verifier),
        passed=verdict == "PASS",
        findings=tuple(item.strip() for item in findings),
    )


def verification_prompt_payload(producer: ProviderBackedAgentResult) -> dict[str, object]:
    execution = producer.execution
    output = execution.route.get("output")
    return {
        "producer_agent_id": execution.admission.agent_id,
        "producer_verifier_id": execution.admission.verifier_id,
        "producer_evidence_digest": producer.evidence_digest,
        "producer_route_sequence": execution.route.get("sequence"),
        "producer_skill_id": execution.route.get("skill_id"),
        "producer_provider_id": execution.route.get("provider_id"),
        "producer_capability": execution.route.get("capability"),
        "producer_output_sha256": hashlib.sha256(
            json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest(),
    }


def _route_digest(execution: NamedAgentExecution) -> str:
    material: dict[str, Any] = {
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
