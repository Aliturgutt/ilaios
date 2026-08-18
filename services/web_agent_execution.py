"""Canonical P1 Web agent bindings on the existing ILAIOS runtime.

The five proposal roles use the same NamedAgentExecutor and governed provider
adapter as P0. BrowserQA is intentionally separate because it consumes real
browser evidence through a deterministic local adapter rather than a text model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
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


class WebAgentExecutionError(RuntimeError):
    """Web agent execution violated a canonical binding or evidence invariant."""


@dataclass(frozen=True, slots=True)
class WebAgentBinding:
    agent_id: str
    primary_skill_id: str
    capability: str
    permission: str
    execution_mode: str


WEB_AGENT_BINDINGS: tuple[WebAgentBinding, ...] = (
    WebAgentBinding("ilaios.agent.web.ux.v1", "ilaios.skill.web.ux.v1", "web.ux", "requirements.read", "governed-ai"),
    WebAgentBinding("ilaios.agent.web.visual.v1", "ilaios.skill.web.visual.v1", "web.visual", "requirements.read", "governed-ai"),
    WebAgentBinding("ilaios.agent.web.asset.v1", "ilaios.skill.web.asset.v1", "web.asset", "asset.read", "governed-ai"),
    WebAgentBinding("ilaios.agent.web.content.v1", "ilaios.skill.web.content.v1", "web.content", "requirements.read", "governed-ai"),
    WebAgentBinding("ilaios.agent.web.seo.v1", "ilaios.skill.web.seo.v1", "web.seo", "site.read", "governed-ai"),
    WebAgentBinding("ilaios.agent.web.browser-qa.v1", "ilaios-web-e2e", "web.verify", "authorized-site.read", "browser-evidence"),
)
_BINDINGS_BY_ID = {item.agent_id: item for item in WEB_AGENT_BINDINGS}


@dataclass(frozen=True, slots=True)
class WebProviderBackedRequest:
    invocation: AgentInvocation
    grant: ExecutionGrant
    tenant_id: str
    scopes: tuple[Scope, ...]
    prompt: str
    input_tokens: int
    max_output_tokens: int
    now: datetime


@dataclass(frozen=True, slots=True)
class WebAgentResult:
    execution: NamedAgentExecution
    evidence_digest: str
    model_id: str | None = None
    provider_id: str | None = None


class WebProviderBackedExecutor:
    """Thin Web binding wrapper over the canonical named/runtime/provider path."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        self._named = named_executor
        self._providers = provider_adapter

    def execute(self, request: WebProviderBackedRequest) -> WebAgentResult:
        binding = web_binding_for(request.invocation.target_id)
        if binding.execution_mode != "governed-ai":
            raise WebAgentExecutionError("Web binding is not provider-backed")
        _validate_invocation(request.invocation, binding)
        if request.prompt != request.invocation.prompt:
            raise WebAgentExecutionError("provider prompt diverges from admitted invocation")
        if not request.invocation.external_egress or not request.invocation.dlp_approved:
            raise WebAgentExecutionError("Web AI execution requires explicit egress and DLP approval")
        if request.now.tzinfo is None:
            raise WebAgentExecutionError("Web execution timestamp must be timezone-aware")
        if request.input_tokens < 0 or request.max_output_tokens <= 0:
            raise WebAgentExecutionError("Web token estimates must be bounded")

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    binding.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                raise WebAgentExecutionError("no governed Web AI fallback remains") from (last_error or exc)
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
                raise WebAgentExecutionError("Web provider output evidence is missing")
            if output.get("model_id") != selection.model_id:
                raise WebAgentExecutionError("Web model identity diverged from selection")
            if output.get("provider_id") != selection.provider_id:
                raise WebAgentExecutionError("Web provider identity diverged from selection")
            return WebAgentResult(
                execution,
                execution_evidence_digest(execution),
                selection.model_id,
                selection.provider_id,
            )


class WebBrowserEvidenceExecutor:
    """Run BrowserQA over an exact real-browser evidence artifact."""

    def __init__(self, named_executor: NamedAgentExecutor, provider_id: str) -> None:
        self._named = named_executor
        self._provider_id = provider_id

    def execute(
        self,
        invocation: AgentInvocation,
        grant: ExecutionGrant,
        *,
        evidence_path: Path,
        source_sha: str,
        now: datetime,
    ) -> WebAgentResult:
        binding = web_binding_for(invocation.target_id)
        if binding.execution_mode != "browser-evidence":
            raise WebAgentExecutionError("Web binding is not browser evidence execution")
        _validate_invocation(invocation, binding)
        if invocation.external_egress or invocation.dlp_approved:
            raise WebAgentExecutionError("Browser evidence verification must be local")
        if now.tzinfo is None:
            raise WebAgentExecutionError("BrowserQA timestamp must be timezone-aware")
        execution = self._named.execute(
            invocation,
            grant,
            skill_id=binding.primary_skill_id,
            payload={
                "evidence_path": str(evidence_path.resolve()),
                "source_sha": source_sha,
            },
            now=now,
            preferred_provider_id=self._provider_id,
        )
        return WebAgentResult(execution, execution_evidence_digest(execution))


def web_binding_for(agent_id: str) -> WebAgentBinding:
    try:
        return _BINDINGS_BY_ID[agent_id]
    except KeyError as exc:
        raise WebAgentExecutionError("agent is outside canonical Web bindings") from exc


def validate_web_agent_bindings() -> None:
    if len(WEB_AGENT_BINDINGS) != 6 or len(_BINDINGS_BY_ID) != 6:
        raise WebAgentExecutionError("Web binding coverage must contain six unique agents")
    for binding in WEB_AGENT_BINDINGS:
        registration = registration_for(binding.agent_id)
        if registration.manifest.team != "web":
            raise WebAgentExecutionError("Web binding references a non-Web agent")
        if binding.capability not in registration.manifest.capabilities:
            raise WebAgentExecutionError("Web binding exceeds agent capability")
        if binding.permission not in registration.manifest.permissions:
            raise WebAgentExecutionError("Web binding exceeds agent permission")
        if binding.execution_mode not in {"governed-ai", "browser-evidence"}:
            raise WebAgentExecutionError("unknown Web execution mode")


def _validate_invocation(invocation: AgentInvocation, binding: WebAgentBinding) -> None:
    if invocation.capability != binding.capability:
        raise WebAgentExecutionError("Web invocation capability diverges from binding")
    if invocation.permission != binding.permission:
        raise WebAgentExecutionError("Web invocation permission diverges from binding")


validate_web_agent_bindings()
