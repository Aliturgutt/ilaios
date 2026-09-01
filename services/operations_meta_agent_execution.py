"""Canonical runtime bindings for Operations 6 + Meta 2 agents.

Operations and SelfDevelopmentCoordinator produce bounded proposals through the
existing NamedAgentExecutor + GovernedRuntime path. IndependentVerifier remains
on the existing independent verification mechanism and is deliberately not
advertised as a generic provider-backed capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_registry import CANONICAL_AGENT_REGISTRY, INDEPENDENT_VERIFIER_ID, registration_for
from services.ai_governance import GovernanceError, Scope
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.runtime import ExecutionGrant
from services.runtime.ai_provider_adapter import (
    AIProviderAuthorizationError,
    AIProviderError,
    AIProviderTransportError,
    GovernedAIProviderAdapter,
)
from services.runtime.routing import RuntimeError as RuntimeRoutingError


class OperationsMetaAgentExecutionError(RuntimeError):
    """Operations/Meta execution violated a canonical runtime boundary."""


@dataclass(frozen=True, slots=True)
class OperationsMetaAgentBinding:
    agent_id: str
    primary_skill_id: str
    capability: str
    permission: str
    execution_mode: str


OPERATIONS_META_AGENT_BINDINGS: tuple[OperationsMetaAgentBinding, ...] = (
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.automation.v1",
        "ilaios.skill.operations.automation.v1",
        "operations.automate",
        "workflow.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.analytics.v1",
        "ilaios.skill.operations.analytics.v1",
        "operations.analyze",
        "telemetry.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.monitoring.v1",
        "ilaios.skill.operations.monitoring.v1",
        "operations.monitor",
        "telemetry.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.recovery.v1",
        "ilaios.skill.operations.recovery.v1",
        "operations.recover",
        "evidence.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.provider-watcher.v1",
        "ilaios.skill.operations.provider-watcher.v1",
        "provider.monitor",
        "provider-health.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.operations.benchmark.v1",
        "ilaios.skill.operations.benchmark.v1",
        "benchmark.evaluate",
        "benchmark-input.read",
        "governed-ai",
    ),
    OperationsMetaAgentBinding(
        INDEPENDENT_VERIFIER_ID,
        "ilaios.skill.meta.independent-verification.v1",
        "evidence.verify",
        "evidence.read",
        "independent-verification",
    ),
    OperationsMetaAgentBinding(
        "ilaios.agent.meta.self-development.v1",
        "ilaios.skill.meta.self-development.v1",
        "self-development.coordinate",
        "repository.read",
        "governed-ai",
    ),
)

_BINDINGS_BY_ID = {item.agent_id: item for item in OPERATIONS_META_AGENT_BINDINGS}
OPERATIONS_META_GOVERNED_AI_CAPABILITIES = frozenset(
    item.capability
    for item in OPERATIONS_META_AGENT_BINDINGS
    if item.execution_mode == "governed-ai"
)


@dataclass(frozen=True, slots=True)
class OperationsMetaProviderBackedAgentRequest:
    invocation: AgentInvocation
    grant: ExecutionGrant
    tenant_id: str
    scopes: tuple[Scope, ...]
    prompt: str
    input_tokens: int
    max_output_tokens: int
    now: datetime


@dataclass(frozen=True, slots=True)
class OperationsMetaProviderBackedAgentResult:
    execution: NamedAgentExecution
    model_id: str
    provider_id: str
    evidence_digest: str


def _bounded_provider_failure_classification(exc: Exception) -> str:
    """Return non-secret provider failure metadata suitable for live CI evidence."""
    chain: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and len(chain) < 6 and id(current) not in seen:
        seen.add(id(current))
        label = type(current).__name__
        if isinstance(current, AIProviderTransportError):
            label += f"(retryable={str(current.retryable).lower()}"
            if current.retry_after_seconds is not None:
                label += f",retry_after_seconds={current.retry_after_seconds:g}"
            label += ")"
        chain.append(label)
        current = current.__cause__
    return ">".join(chain)


class OperationsMetaProviderBackedExecutor:
    """Execute bounded Operations/Meta proposals through canonical runtime."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        # Lazy import avoids a module cycle while keeping skill provisioning
        # additive and idempotent on the already-composed canonical runtime.
        from services.operations_meta_agent_skill_catalog import (
            ensure_operations_meta_agent_skills,
        )

        ensure_operations_meta_agent_skills(named_executor)
        self._named = named_executor
        self._providers = provider_adapter

    def execute(
        self,
        request: OperationsMetaProviderBackedAgentRequest,
    ) -> OperationsMetaProviderBackedAgentResult:
        binding = operations_meta_binding_for(request.invocation.target_id)
        if binding.execution_mode != "governed-ai":
            raise OperationsMetaAgentExecutionError(
                "binding is not provider-backed governed AI execution"
            )
        if request.invocation.capability != binding.capability:
            raise OperationsMetaAgentExecutionError(
                "invocation capability diverges from Operations/Meta binding"
            )
        if request.invocation.permission != binding.permission:
            raise OperationsMetaAgentExecutionError(
                "invocation permission diverges from Operations/Meta binding"
            )
        if request.prompt != request.invocation.prompt:
            raise OperationsMetaAgentExecutionError(
                "provider prompt must equal admitted invocation prompt"
            )
        if not request.invocation.external_egress or not request.invocation.dlp_approved:
            raise OperationsMetaAgentExecutionError(
                "external AI execution requires explicit egress and DLP approval"
            )
        if request.now.tzinfo is None:
            raise OperationsMetaAgentExecutionError(
                "execution timestamp must be timezone-aware"
            )
        if request.input_tokens < 0 or request.max_output_tokens <= 0:
            raise OperationsMetaAgentExecutionError("token estimates must be bounded")

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    binding.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                detail = (
                    ""
                    if last_error is None
                    else "; last_failure=" + _bounded_provider_failure_classification(last_error)
                )
                raise OperationsMetaAgentExecutionError(
                    "no governed Operations/Meta AI fallback remains" + detail
                ) from (last_error or exc)

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
                raise OperationsMetaAgentExecutionError(
                    "AI provider credential, permission, or billing gate failed"
                ) from exc
            except (AIProviderError, GovernanceError, RuntimeRoutingError) as exc:
                denied_models.add(selection.model_id)
                last_error = exc
                continue

            output = execution.route.get("output")
            if not isinstance(output, dict):
                raise OperationsMetaAgentExecutionError("provider output evidence is missing")
            if output.get("model_id") != selection.model_id:
                raise OperationsMetaAgentExecutionError(
                    "persisted model identity diverged from selection"
                )
            if output.get("provider_id") != selection.provider_id:
                raise OperationsMetaAgentExecutionError(
                    "persisted provider identity diverged from selection"
                )
            return OperationsMetaProviderBackedAgentResult(
                execution=execution,
                model_id=selection.model_id,
                provider_id=selection.provider_id,
                evidence_digest=execution_evidence_digest(execution),
            )


def operations_meta_binding_for(agent_id: str) -> OperationsMetaAgentBinding:
    try:
        return _BINDINGS_BY_ID[agent_id]
    except KeyError as exc:
        raise OperationsMetaAgentExecutionError(
            "agent is outside Operations/Meta execution bindings"
        ) from exc


def validate_operations_meta_agent_bindings() -> None:
    expected_ids = {
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team in {"operations", "meta"}
    }
    configured_ids = set(_BINDINGS_BY_ID)
    if configured_ids != expected_ids:
        raise OperationsMetaAgentExecutionError(
            "Operations/Meta binding coverage mismatch "
            f"missing={sorted(expected_ids-configured_ids)} "
            f"extra={sorted(configured_ids-expected_ids)}"
        )
    if len(OPERATIONS_META_AGENT_BINDINGS) != 8:
        raise OperationsMetaAgentExecutionError(
            "Operations/Meta execution population must be eight"
        )
    for binding in OPERATIONS_META_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        if binding.capability not in manifest.capabilities:
            raise OperationsMetaAgentExecutionError(
                f"binding capability exceeds manifest: {binding.agent_id}"
            )
        if binding.permission not in manifest.permissions:
            raise OperationsMetaAgentExecutionError(
                f"binding permission exceeds manifest: {binding.agent_id}"
            )
    verifier = operations_meta_binding_for(INDEPENDENT_VERIFIER_ID)
    if verifier.execution_mode != "independent-verification":
        raise OperationsMetaAgentExecutionError(
            "IndependentVerifier must remain outside generic provider execution"
        )
    if "evidence.verify" in OPERATIONS_META_GOVERNED_AI_CAPABILITIES:
        raise OperationsMetaAgentExecutionError(
            "provider boundary must not own evidence verification authority"
        )


validate_operations_meta_agent_bindings()
