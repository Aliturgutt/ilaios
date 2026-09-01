"""Canonical execution bindings for the six Web agents.

The module is additive: provider-backed proposal roles execute through the existing
NamedAgentExecutor/GovernedRuntime and governed AI adapter. BrowserQA remains a
real ToolGateway/browser path and is never replaced by a generic LLM call.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_registry import CANONICAL_AGENT_REGISTRY, registration_for
from services.ai_governance import GovernanceError, Scope
from services.named_agent_executor import NamedAgentExecution, NamedAgentExecutor
from services.runtime import ExecutionGrant
from services.runtime.ai_provider_adapter import (
    AIProviderAuthorizationError,
    AIProviderError,
    GovernedAIProviderAdapter,
)
from services.runtime.routing import RuntimeError as RuntimeRoutingError


class WebAgentExecutionError(RuntimeError):
    """A Web agent execution violated its canonical identity/runtime boundary."""


@dataclass(frozen=True, slots=True)
class WebAgentBinding:
    agent_id: str
    primary_skill_id: str
    capability: str
    permission: str
    execution_mode: str


WEB_AGENT_BINDINGS: tuple[WebAgentBinding, ...] = (
    WebAgentBinding(
        "ilaios.agent.web.ux.v1",
        "ilaios.skill.web.ux.v1",
        "web.ux",
        "requirements.read",
        "governed-ai",
    ),
    WebAgentBinding(
        "ilaios.agent.web.visual.v1",
        "ilaios.skill.web.visual.v1",
        "web.visual",
        "requirements.read",
        "governed-ai",
    ),
    WebAgentBinding(
        "ilaios.agent.web.asset.v1",
        "ilaios.skill.web.asset.v1",
        "web.asset",
        "asset.read",
        "governed-ai",
    ),
    WebAgentBinding(
        "ilaios.agent.web.content.v1",
        "ilaios.skill.web.content.v1",
        "web.content",
        "requirements.read",
        "governed-ai",
    ),
    WebAgentBinding(
        "ilaios.agent.web.seo.v1",
        "ilaios.skill.web.seo.v1",
        "web.seo",
        "site.read",
        "governed-ai",
    ),
    WebAgentBinding(
        "ilaios.agent.web.browser-qa.v1",
        "ilaios-web-e2e",
        "web.verify",
        "authorized-site.read",
        "browser-tool",
    ),
)

_WEB_BINDINGS_BY_ID = {item.agent_id: item for item in WEB_AGENT_BINDINGS}
WEB_GOVERNED_AI_CAPABILITIES = frozenset(
    item.capability for item in WEB_AGENT_BINDINGS if item.execution_mode == "governed-ai"
)


@dataclass(frozen=True, slots=True)
class WebProviderBackedAgentRequest:
    invocation: AgentInvocation
    grant: ExecutionGrant
    tenant_id: str
    scopes: tuple[Scope, ...]
    prompt: str
    input_tokens: int
    max_output_tokens: int
    now: datetime


@dataclass(frozen=True, slots=True)
class WebProviderBackedAgentResult:
    execution: NamedAgentExecution
    model_id: str
    provider_id: str
    evidence_digest: str


class WebProviderBackedExecutor:
    """Execute Web proposal agents through the canonical governed runtime."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        self._named = named_executor
        self._providers = provider_adapter

    def execute(
        self, request: WebProviderBackedAgentRequest
    ) -> WebProviderBackedAgentResult:
        binding = web_binding_for(request.invocation.target_id)
        if binding.execution_mode != "governed-ai":
            raise WebAgentExecutionError("Web binding is not provider-backed")
        if request.invocation.capability != binding.capability:
            raise WebAgentExecutionError("invocation capability diverges from Web binding")
        if request.invocation.permission != binding.permission:
            raise WebAgentExecutionError("invocation permission diverges from Web binding")
        if request.prompt != request.invocation.prompt:
            raise WebAgentExecutionError("provider prompt must equal admitted invocation prompt")
        if not request.invocation.external_egress or not request.invocation.dlp_approved:
            raise WebAgentExecutionError(
                "external Web AI execution requires explicit egress and DLP approval"
            )
        if request.now.tzinfo is None:
            raise WebAgentExecutionError("execution timestamp must be timezone-aware")
        if request.input_tokens < 0 or request.max_output_tokens <= 0:
            raise WebAgentExecutionError("token estimates must be bounded")

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    binding.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                raise WebAgentExecutionError("no governed Web AI fallback remains") from (
                    last_error or exc
                )

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
                raise WebAgentExecutionError(
                    "Web AI provider credential, permission, or billing gate failed"
                ) from exc
            except (AIProviderError, GovernanceError, RuntimeRoutingError) as exc:
                denied_models.add(selection.model_id)
                last_error = exc
                continue

            output = execution.route.get("output")
            if not isinstance(output, dict):
                raise WebAgentExecutionError("provider output evidence is missing")
            if output.get("model_id") != selection.model_id:
                raise WebAgentExecutionError("persisted model identity diverged from selection")
            if output.get("provider_id") != selection.provider_id:
                raise WebAgentExecutionError("persisted provider identity diverged from selection")
            return WebProviderBackedAgentResult(
                execution=execution,
                model_id=selection.model_id,
                provider_id=selection.provider_id,
                evidence_digest=execution_evidence_digest(execution),
            )


def web_binding_for(agent_id: str) -> WebAgentBinding:
    try:
        return _WEB_BINDINGS_BY_ID[agent_id]
    except KeyError as exc:
        raise WebAgentExecutionError("agent is outside Web execution bindings") from exc


def validate_web_agent_bindings() -> None:
    expected_ids = {
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team == "web"
    }
    configured_ids = set(_WEB_BINDINGS_BY_ID)
    if configured_ids != expected_ids:
        raise WebAgentExecutionError(
            f"Web binding coverage mismatch missing={sorted(expected_ids-configured_ids)} "
            f"extra={sorted(configured_ids-expected_ids)}"
        )
    if len(WEB_AGENT_BINDINGS) != 6:
        raise WebAgentExecutionError("Web execution binding population must be six")
    for binding in WEB_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        if binding.capability not in manifest.capabilities:
            raise WebAgentExecutionError(
                f"binding capability exceeds manifest: {binding.agent_id}"
            )
        if binding.permission not in manifest.permissions:
            raise WebAgentExecutionError(
                f"binding permission exceeds manifest: {binding.agent_id}"
            )
        if binding.execution_mode not in {"governed-ai", "browser-tool"}:
            raise WebAgentExecutionError("unknown Web execution mode")
    browser = web_binding_for("ilaios.agent.web.browser-qa.v1")
    if browser.execution_mode != "browser-tool" or browser.capability != "web.verify":
        raise WebAgentExecutionError("BrowserQA must remain on real browser-tool execution")
    if len(WEB_GOVERNED_AI_CAPABILITIES) != 5:
        raise WebAgentExecutionError("five Web agents must use governed AI proposal execution")


validate_web_agent_bindings()
