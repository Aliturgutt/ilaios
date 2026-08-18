"""P0 red-team E2E proofs for governed provider-backed named-agent execution."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from services.agent_governance import AgentInvocation
from services.agent_registry import ORCHESTRATOR_ID
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
from services.named_agent_executor import NamedAgentExecutor
from services.p0_agent_execution import (
    P0_AGENT_BINDINGS,
    P0AgentExecutionError,
    P0ProviderBackedExecutor,
    ProviderBackedAgentRequest,
    validate_p0_bindings,
)
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.ai_provider_adapter import (
    GovernedAIProviderAdapter,
    ProviderEndpoint,
    ProviderTransportResult,
)

NOW = datetime(2026, 8, 18, 9, 0, tzinfo=timezone.utc)
PLANNER_ID = "ilaios.agent.core.planner.v1"
TENANT_SCOPE = Scope(ScopeKind.TENANT, "tenant-test")


class _FallbackTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        self.calls.append(endpoint.provider_id)
        assert api_key == "test-secret"
        if endpoint.provider_id == "provider-a":
            raise RuntimeError("simulated provider outage")
        return ProviderTransportResult(
            "bounded execution plan",
            input_tokens=24,
            output_tokens=18,
            response_id="response-b",
        )


def _limits() -> UsageLimits:
    return UsageLimits(
        max_input_tokens=4096,
        max_output_tokens=1024,
        max_requests_daily=20,
        max_concurrency=4,
        daily_cost=Decimal("10"),
        monthly_cost=Decimal("100"),
        gpu_seconds_daily=Decimal("1000"),
        runtime_seconds_daily=Decimal("1000"),
        max_retries=1,
        max_retry_cost=Decimal("1"),
    )


def _provider_stack(tmp_path: Path) -> tuple[P0ProviderBackedExecutor, NamedAgentExecutor, _FallbackTransport]:
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("provider-a", "openai-compatible"))
    registry.register_provider(ProviderRecord("provider-b", "openai-compatible"))
    registry.register_model(
        ModelRecord(
            "model-a",
            "provider-a",
            frozenset({"workflow.plan"}),
            context_window=8192,
            max_output_tokens=1024,
            input_cost_per_million=Decimal("1"),
            output_cost_per_million=Decimal("2"),
        )
    )
    registry.register_model(
        ModelRecord(
            "model-b",
            "provider-b",
            frozenset({"workflow.plan"}),
            context_window=8192,
            max_output_tokens=1024,
            input_cost_per_million=Decimal("1"),
            output_cost_per_million=Decimal("2"),
        )
    )
    governor = UsageGovernor(registry, {TENANT_SCOPE: _limits()})
    transport = _FallbackTransport()
    adapter = GovernedAIProviderAdapter(
        registry,
        RoutingPolicy(fallback_order=("model-a", "model-b")),
        governor,
        (
            ProviderEndpoint("provider-a", "https://provider-a.invalid/v1", "P_A", max_retries=0),
            ProviderEndpoint("provider-b", "https://provider-b.invalid/v1", "P_B", max_retries=0),
        ),
        transport=transport,
        secret_reader=lambda _: "test-secret",
    )

    database = tmp_path / "p0-runtime.sqlite3"
    migrate_database(database)
    runtime = GovernedRuntime(database, external_adapters=adapter.runtime_adapters())
    named = NamedAgentExecutor(runtime, GrantPolicy())
    named.provision_agent(PLANNER_ID)
    named.provision_skill(
        "ilaios.skill.core.planning.v1",
        b"ILAIOS first-party bounded planning skill",
        frozenset({"workflow.plan"}),
    )
    for provider_id in ("provider-a", "provider-b"):
        named.provision_provider(
            provider_id,
            frozenset({"workflow.plan"}),
            adapter_kind=adapter.adapter_kind(provider_id),
        )
    return P0ProviderBackedExecutor(named, adapter), named, transport


def _grant() -> ExecutionGrant:
    return ExecutionGrant(
        "grant-planner",
        PLANNER_ID,
        frozenset({"workflow.read"}),
        frozenset({PLANNER_ID}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def _invocation(*, dlp_approved: bool = True) -> AgentInvocation:
    return AgentInvocation(
        "invoke-planner",
        ORCHESTRATOR_ID,
        PLANNER_ID,
        "workflow.plan",
        "workflow.read",
        "governed_task",
        "proposal",
        "Plan the bounded authorized software task.",
        external_egress=True,
        dlp_approved=dlp_approved,
        security_scan_passed=True,
    )


def test_p0_bindings_cover_exact_21_agents() -> None:
    validate_p0_bindings()
    assert len(P0_AGENT_BINDINGS) == 21
    assert sum(item.execution_mode == "governed-ai" for item in P0_AGENT_BINDINGS) == 16
    assert sum(item.execution_mode == "defensive-local" for item in P0_AGENT_BINDINGS) == 4
    assert sum(item.execution_mode == "independent-verification" for item in P0_AGENT_BINDINGS) == 1


def test_core_agent_falls_back_and_persists_only_successful_governed_route(tmp_path: Path) -> None:
    executor, named, transport = _provider_stack(tmp_path)
    invocation = _invocation()
    result = executor.execute(
        ProviderBackedAgentRequest(
            invocation=invocation,
            grant=_grant(),
            tenant_id="tenant-test",
            scopes=(TENANT_SCOPE,),
            prompt=invocation.prompt,
            input_tokens=32,
            max_output_tokens=128,
            now=NOW,
        )
    )

    assert transport.calls == ["provider-a", "provider-b"]
    assert result.model_id == "model-b"
    assert result.provider_id == "provider-b"
    assert len(result.evidence_digest) == 64
    assert result.execution.route["provider_id"] == "provider-b"
    assert result.execution.route["output"]["response_id"] == "response-b"
    assert result.execution.route["output"]["input_tokens"] == 24
    assert result.execution.route["output"]["output_tokens"] == 18
    routes = named.routes()
    assert len(routes) == 1
    assert routes[0]["agent_id"] == PLANNER_ID
    assert routes[0]["provider_id"] == "provider-b"


def test_external_ai_execution_without_dlp_never_reaches_provider(tmp_path: Path) -> None:
    executor, named, transport = _provider_stack(tmp_path)
    invocation = _invocation(dlp_approved=False)
    with pytest.raises(P0AgentExecutionError, match="DLP"):
        executor.execute(
            ProviderBackedAgentRequest(
                invocation=invocation,
                grant=_grant(),
                tenant_id="tenant-test",
                scopes=(TENANT_SCOPE,),
                prompt=invocation.prompt,
                input_tokens=32,
                max_output_tokens=128,
                now=NOW,
            )
        )
    assert transport.calls == []
    assert named.routes() == ()


def test_defensive_security_agent_cannot_be_silently_rerouted_to_ai(tmp_path: Path) -> None:
    executor, _, _ = _provider_stack(tmp_path)
    invocation = AgentInvocation(
        "invoke-codesec",
        ORCHESTRATOR_ID,
        "ilaios.agent.security.codesec.v1",
        "security.sast",
        "repository.read",
        "governed_task",
        "proposal",
        "Scan only the authorized repository scope.",
        external_egress=True,
        dlp_approved=True,
        security_scan_passed=True,
    )
    with pytest.raises(P0AgentExecutionError, match="not provider-backed"):
        executor.execute(
            ProviderBackedAgentRequest(
                invocation=invocation,
                grant=_grant(),
                tenant_id="tenant-test",
                scopes=(TENANT_SCOPE,),
                prompt=invocation.prompt,
                input_tokens=20,
                max_output_tokens=64,
                now=NOW,
            )
        )
