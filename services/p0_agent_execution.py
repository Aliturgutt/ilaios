"""P0 execution bindings for Core, Engineering, and defensive Security agents.

The service composes the existing NamedAgentExecutor, canonical GovernedRuntime,
and AI governance/provider adapter. It is not a second agent engine. Static
bindings establish which primary skill/capability/permission path must pass E2E
before each P0 identity can earn EXECUTABLE readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_readiness import p0_registrations
from services.agent_registry import registration_for
from services.ai_governance import GovernanceError, Scope
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.runtime import ExecutionGrant
from services.runtime.ai_provider_adapter import (
    AIProviderAuthorizationError,
    AIProviderError,
    GovernedAIProviderAdapter,
)
from services.runtime.routing import RuntimeError as RuntimeRoutingError


class P0AgentExecutionError(RuntimeError):
    """P0 execution violated a canonical binding or provider invariant."""


@dataclass(frozen=True, slots=True)
class P0AgentBinding:
    agent_id: str
    primary_skill_id: str
    capability: str
    permission: str
    execution_mode: str


P0_AGENT_BINDINGS: tuple[P0AgentBinding, ...] = (
    P0AgentBinding("ilaios.agent.core.orchestrator.v1", "ilaios.skill.core.orchestration.v1", "workflow.coordinate", "workflow.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.core.planner.v1", "ilaios.skill.core.planning.v1", "workflow.plan", "workflow.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.core.supervisor.v1", "ilaios.skill.core.supervision.v1", "workflow.supervise", "workflow.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.core.policy.v1", "ilaios.skill.core.policy.v1", "policy.evaluate", "policy.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.core.cost-resource.v1", "ilaios.skill.core.cost-resource.v1", "cost.evaluate", "usage.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.architect.v1", "sf-architecture-planning", "architecture.propose", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.core.v1", "sf-core-engineering", "code.propose", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.frontend.v1", "sf-frontend-engineering", "frontend.propose", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.backend.v1", "sf-backend-engineering", "backend.propose", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.integration.v1", "sf-integration-engineering", "integration.propose", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.test.v1", "sf-test-design", "test.design", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.review.v1", "sf-code-review", "code.review", "repository.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.runtime-qa.v1", "sf-runtime-qa", "runtime.verify", "telemetry.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.release.v1", "sf-release-readiness", "release.assess", "evidence.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.engineering.recovery.v1", "sf-recovery", "recovery.propose", "evidence.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.security.coordinator.v1", "ilaios.skill.security.coordinate.v1", "security.coordinate", "scope.read", "governed-ai"),
    P0AgentBinding("ilaios.agent.security.codesec.v1", "ilaios.skill.security.sast.v1", "security.sast", "repository.read", "defensive-local"),
    P0AgentBinding("ilaios.agent.security.web-api.v1", "ilaios.skill.security.web-api.v1", "security.web-api", "authorized-target.read", "defensive-local"),
    P0AgentBinding("ilaios.agent.security.supply-chain.v1", "ilaios.skill.security.supply-chain.v1", "security.dependency", "repository.read", "defensive-local"),
    P0AgentBinding("ilaios.agent.security.infrastructure.v1", "ilaios.skill.security.infrastructure.v1", "security.infrastructure", "authorized-config.read", "defensive-local"),
    P0AgentBinding("ilaios.agent.security.verifier.v1", "ilaios.skill.security.verify.v1", "security.verify", "evidence.read", "independent-verification"),
)

_BINDINGS_BY_ID = {item.agent_id: item for item in P0_AGENT_BINDINGS}


@dataclass(frozen=True, slots=True)
class ProviderBackedAgentRequest:
    invocation: AgentInvocation
    grant: ExecutionGrant
    tenant_id: str
    scopes: tuple[Scope, ...]
    prompt: str
    input_tokens: int
    max_output_tokens: int
    now: datetime


@dataclass(frozen=True, slots=True)
class ProviderBackedAgentResult:
    execution: NamedAgentExecution
    model_id: str
    provider_id: str
    evidence_digest: str


class P0ProviderBackedExecutor:
    """Execute P0 governed-AI bindings through the canonical named/runtime path."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        self._named = named_executor
        self._providers = provider_adapter

    def execute(self, request: ProviderBackedAgentRequest) -> ProviderBackedAgentResult:
        binding = binding_for(request.invocation.target_id)
        if binding.execution_mode != "governed-ai":
            raise P0AgentExecutionError("binding is not provider-backed AI execution")
        if request.invocation.capability != binding.capability:
            raise P0AgentExecutionError("invocation capability diverges from P0 binding")
        if request.invocation.permission != binding.permission:
            raise P0AgentExecutionError("invocation permission diverges from P0 binding")
        if request.prompt != request.invocation.prompt:
            raise P0AgentExecutionError("provider prompt must equal admitted invocation prompt")
        if not request.invocation.external_egress or not request.invocation.dlp_approved:
            raise P0AgentExecutionError("external AI execution requires explicit egress and DLP approval")
        if request.now.tzinfo is None:
            raise P0AgentExecutionError("execution timestamp must be timezone-aware")
        if request.input_tokens < 0 or request.max_output_tokens <= 0:
            raise P0AgentExecutionError("token estimates must be bounded")

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    binding.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                raise P0AgentExecutionError("no governed AI fallback remains") from (last_error or exc)

            payload = {
                "request_id": request.invocation.invocation_id,
                "tenant_id": request.tenant_id,
                "model_id": selection.model_id,
                "prompt": request.prompt,
                "input_tokens": request.input_tokens,
                "max_output_tokens": request.max_output_tokens,
                "scopes": [
                    {"kind": scope.kind.value, "scope_id": scope.scope_id}
                    for scope in request.scopes
                ],
                "now": request.now.isoformat(),
            }
            try:
                execution = self._named.execute(
                    request.invocation,
                    request.grant,
                    skill_id=binding.primary_skill_id,
                    payload=payload,
                    now=request.now,
                    preferred_provider_id=selection.provider_id,
                )
            except AIProviderAuthorizationError as exc:
                raise P0AgentExecutionError(
                    "AI provider credential, permission, or billing gate failed"
                ) from exc
            except (AIProviderError, GovernanceError, RuntimeRoutingError) as exc:
                denied_models.add(selection.model_id)
                last_error = exc
                continue

            output = execution.route.get("output")
            if not isinstance(output, dict):
                raise P0AgentExecutionError("provider output evidence is missing")
            if output.get("model_id") != selection.model_id:
                raise P0AgentExecutionError("persisted model identity diverged from selection")
            if output.get("provider_id") != selection.provider_id:
                raise P0AgentExecutionError("persisted provider identity diverged from selection")
            evidence_digest = execution_evidence_digest(execution)
            return ProviderBackedAgentResult(
                execution,
                selection.model_id,
                selection.provider_id,
                evidence_digest,
            )


def binding_for(agent_id: str) -> P0AgentBinding:
    try:
        return _BINDINGS_BY_ID[agent_id]
    except KeyError as exc:
        raise P0AgentExecutionError("agent is outside P0 execution bindings") from exc


def validate_p0_bindings() -> None:
    expected_ids = {item.manifest.agent_id for item in p0_registrations()}
    configured_ids = set(_BINDINGS_BY_ID)
    if configured_ids != expected_ids:
        raise P0AgentExecutionError(
            f"P0 binding coverage mismatch missing={sorted(expected_ids-configured_ids)} "
            f"extra={sorted(configured_ids-expected_ids)}"
        )
    for binding in P0_AGENT_BINDINGS:
        registration = registration_for(binding.agent_id)
        manifest = registration.manifest
        if binding.capability not in manifest.capabilities:
            raise P0AgentExecutionError(f"binding capability exceeds manifest: {binding.agent_id}")
        if binding.permission not in manifest.permissions:
            raise P0AgentExecutionError(f"binding permission exceeds manifest: {binding.agent_id}")
        if binding.execution_mode not in {"governed-ai", "defensive-local", "independent-verification"}:
            raise P0AgentExecutionError("unknown P0 execution mode")


validate_p0_bindings()
