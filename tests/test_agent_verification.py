"""Red-team tests for producer/verifier separation and exact evidence binding."""

from datetime import datetime, timezone

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.agent_verification import (
    AgentVerificationError,
    compile_independent_verification,
    verification_prompt_payload,
)
from services.named_agent_executor import NamedAgentExecution
from services.p0_agent_execution import ProviderBackedAgentResult

NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)
PRODUCER_ID = "ilaios.agent.engineering.core.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"


def _producer() -> ProviderBackedAgentResult:
    execution = NamedAgentExecution(
        AgentAdmissionEvidence(
            "producer-invocation",
            PRODUCER_ID,
            VERIFIER_ID,
            NOW,
            True,
            True,
        ),
        {
            "sequence": 4,
            "agent_id": PRODUCER_ID,
            "skill_id": "sf-core-engineering",
            "provider_id": "provider-a",
            "capability": "code.propose",
            "output": {
                "text": "bounded producer result",
                "model_id": "model-a",
                "provider_id": "provider-a",
            },
        },
    )
    return ProviderBackedAgentResult(
        execution=execution,
        model_id="model-a",
        provider_id="provider-a",
        evidence_digest="a" * 64,
    )


def _verifier(text: str, *, agent_id: str = VERIFIER_ID) -> NamedAgentExecution:
    return NamedAgentExecution(
        AgentAdmissionEvidence(
            "verifier-invocation",
            agent_id,
            "human.owner",
            NOW,
            True,
            True,
        ),
        {
            "sequence": 5,
            "agent_id": agent_id,
            "skill_id": "ilaios.skill.meta.independent-verification.v1",
            "provider_id": "provider-b",
            "capability": "evidence.verify",
            "output": {
                "text": text,
                "model_id": "model-b",
                "provider_id": "provider-b",
            },
        },
    )


def test_pass_verdict_requires_exact_producer_digest_and_no_findings() -> None:
    producer = _producer()
    verifier = _verifier(
        '{"verdict":"PASS","producer_evidence_digest":"'
        + producer.evidence_digest
        + '","findings":[]}'
    )
    verdict = compile_independent_verification(producer, verifier)
    assert verdict.passed is True
    assert verdict.producer_agent_id == PRODUCER_ID
    assert verdict.verifier_agent_id == VERIFIER_ID
    assert verdict.producer_evidence_digest == producer.evidence_digest
    assert len(verdict.verifier_route_digest) == 64


def test_verifier_cannot_attest_different_evidence() -> None:
    producer = _producer()
    verifier = _verifier(
        '{"verdict":"PASS","producer_evidence_digest":"'
        + ("b" * 64)
        + '","findings":[]}'
    )
    with pytest.raises(AgentVerificationError, match="exact producer evidence"):
        compile_independent_verification(producer, verifier)


def test_producer_cannot_self_verify() -> None:
    producer = _producer()
    verifier = _verifier(
        '{"verdict":"PASS","producer_evidence_digest":"'
        + producer.evidence_digest
        + '","findings":[]}',
        agent_id=PRODUCER_ID,
    )
    with pytest.raises(AgentVerificationError, match="itself"):
        compile_independent_verification(producer, verifier)


def test_fail_verdict_requires_findings() -> None:
    producer = _producer()
    verifier = _verifier(
        '{"verdict":"FAIL","producer_evidence_digest":"'
        + producer.evidence_digest
        + '","findings":[]}'
    )
    with pytest.raises(AgentVerificationError, match="requires at least one finding"):
        compile_independent_verification(producer, verifier)


def test_verification_envelope_does_not_embed_raw_producer_output() -> None:
    producer = _producer()
    envelope = verification_prompt_payload(producer)
    assert envelope["producer_evidence_digest"] == producer.evidence_digest
    assert "producer_output_sha256" in envelope
    assert "producer_output" not in envelope
