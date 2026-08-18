"""Canonical provider-backed IndependentVerifier E2E tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.ai_governance import (
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
)
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import (
    IndependentVerifierExecutionError,
    IndependentVerifierExecutor,
    ProducerEvidence,
)
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.p0_skill_catalog import INDEPENDENT_VERIFIER_SKILL
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.ai_provider_adapter import (
    GovernedAIProviderAdapter,
    ProviderEndpoint,
    ProviderTransportResult,
)

NOW = datetime(2026, 8, 18, 12, 30, tzinfo=timezone.utc)
PRODUCER_ID = "ilaios.agent.engineering.core.v1"
TENANT = Scope(ScopeKind.TENANT, "tenant-verifier")


class _VerifierTransport:
    def __init__(self, producer_digest: str, *, wrong_digest: bool = False) -> None:
        self.producer_digest = producer_digest
        self.wrong_digest = wrong_digest
        self.prompts: list[str] = []

    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        system_instructions: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        assert endpoint.provider_id == "verifier-provider"
        assert model_id == "verifier-model"
        assert api_key == "verifier-secret"
        assert "IndependentVerifier" in system_instructions
        self.prompts.append(prompt)
        digest = "b" * 64 if self.wrong_digest else self.producer_digest
        return ProviderTransportResult(
            '{"verdict":"PASS","producer_evidence_digest":"'
            + digest
            + '","findings":[]}',
            input_tokens=64,
            output_tokens=32,
            response_id="verify-response",
        )


def _producer() -> ProducerEvidence:
    execution = NamedAgentExecution(
        AgentAdmissionEvidence(
            "producer-invocation",
            PRODUCER_ID,
            INDEPENDENT_VERIFIER_ID,
            NOW,
            True,
            True,
        ),
        {
            "sequence": 3,
            "agent_id": PRODUCER_ID,
            "skill_id": "sf-core-engineering",
            "provider_id": "producer-provider",
            "capability": "code.propose",
            "output": {
                "text": "sensitive raw producer body must not be forwarded",
                "model_id": "producer-model",
            },
        },
    )
    return ProducerEvidence(execution, "a" * 64)


def _executor(
    tmp_path: Path, transport: _VerifierTransport
) -> tuple[IndependentVerifierExecutor, NamedAgentExecutor]:
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("verifier-provider", "openai-compatible"))
    registry.register_model(
        ModelRecord(
            "verifier-model",
            "verifier-provider",
            frozenset({"evidence.verify"}),
            context_window=8192,
            max_output_tokens=1024,
            input_cost_per_million=Decimal("1"),
            output_cost_per_million=Decimal("2"),
        )
    )
    limits = UsageLimits(
        4096,
        1024,
        20,
        2,
        Decimal("5"),
        Decimal("50"),
        Decimal("0"),
        Decimal("100"),
        max_retries=1,
        max_retry_cost=Decimal("1"),
    )
    adapter = GovernedAIProviderAdapter(
        registry,
        RoutingPolicy(fallback_order=("verifier-model",)),
        UsageGovernor(registry, {TENANT: limits}),
        (
            ProviderEndpoint(
                "verifier-provider",
                "https://verifier.invalid/v1",
                "VERIFIER_KEY",
                max_retries=0,
            ),
        ),
        transport=transport,
        secret_reader=lambda _: "verifier-secret",
    )
    database = tmp_path / "verifier.sqlite3"
    migrate_database(database)
    runtime = GovernedRuntime(database, external_adapters=adapter.runtime_adapters())
    named = NamedAgentExecutor(runtime, GrantPolicy())
    named.provision_agent(INDEPENDENT_VERIFIER_ID)
    named.provision_skill(
        INDEPENDENT_VERIFIER_SKILL.skill_id,
        INDEPENDENT_VERIFIER_SKILL.content(),
        frozenset({INDEPENDENT_VERIFIER_SKILL.capability}),
    )
    named.provision_provider(
        "verifier-provider",
        frozenset({"evidence.verify"}),
        adapter_kind=adapter.adapter_kind("verifier-provider"),
        deterministic=False,
    )
    return IndependentVerifierExecutor(named, adapter), named


def _grant() -> ExecutionGrant:
    return ExecutionGrant(
        "grant-independent-verifier",
        INDEPENDENT_VERIFIER_ID,
        frozenset({"evidence.read"}),
        frozenset({INDEPENDENT_VERIFIER_ID}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def test_independent_verifier_attests_exact_digest_without_raw_producer_body(
    tmp_path: Path,
) -> None:
    producer = _producer()
    transport = _VerifierTransport(producer.evidence_digest)
    executor, named = _executor(tmp_path, transport)
    result = executor.verify(
        producer,
        _grant(),
        tenant_id="tenant-verifier",
        scopes=(TENANT,),
        now=NOW,
    )
    assert result.passed is True
    assert result.producer_agent_id == PRODUCER_ID
    assert result.producer_evidence_digest == producer.evidence_digest
    assert result.verifier_execution.admission.agent_id == INDEPENDENT_VERIFIER_ID
    assert result.provider_id == "verifier-provider"
    assert len(result.verifier_evidence_digest) == 64
    assert len(named.routes()) == 1
    assert "sensitive raw producer body" not in transport.prompts[0]
    assert producer.evidence_digest in transport.prompts[0]


def test_wrong_digest_verdict_fails_closed(tmp_path: Path) -> None:
    producer = _producer()
    transport = _VerifierTransport(producer.evidence_digest, wrong_digest=True)
    executor, _ = _executor(tmp_path, transport)
    with pytest.raises(IndependentVerifierExecutionError, match="exact producer evidence"):
        executor.verify(
            producer,
            _grant(),
            tenant_id="tenant-verifier",
            scopes=(TENANT,),
            now=NOW,
        )


def test_producer_not_assigned_to_independent_verifier_is_rejected(tmp_path: Path) -> None:
    producer = _producer()
    altered = ProducerEvidence(
        NamedAgentExecution(
            AgentAdmissionEvidence(
                producer.execution.admission.invocation_id,
                producer.execution.admission.agent_id,
                "ilaios.agent.security.verifier.v1",
                NOW,
                True,
                True,
            ),
            producer.execution.route,
        ),
        producer.evidence_digest,
    )
    executor, _ = _executor(tmp_path, _VerifierTransport(producer.evidence_digest))
    with pytest.raises(IndependentVerifierExecutionError, match="not canonically assigned"):
        executor.verify(
            altered,
            _grant(),
            tenant_id="tenant-verifier",
            scopes=(TENANT,),
            now=NOW,
        )
