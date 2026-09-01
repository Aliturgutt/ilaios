"""Canonical governed-AI bindings for Media and Intelligence agents.

These agents produce bounded proposals only. Real video generation/editing/publishing,
source acquisition, and other side effects remain behind the existing Factory,
Policy, Approval, Tool Gateway, provider, and evidence boundaries.
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


class MediaIntelligenceAgentExecutionError(RuntimeError):
    """A Media/Intelligence execution violated canonical runtime boundaries."""


@dataclass(frozen=True, slots=True)
class MediaIntelligenceAgentBinding:
    agent_id: str
    primary_skill_id: str
    capability: str
    permission: str
    execution_mode: str = "governed-ai"


MEDIA_INTELLIGENCE_AGENT_BINDINGS: tuple[MediaIntelligenceAgentBinding, ...] = (
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.story.v1",
        "ilaios.skill.media.story.v1",
        "media.story",
        "brief.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.scene-director.v1",
        "ilaios.skill.media.scene-director.v1",
        "media.scene-plan",
        "script.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.generation.v1",
        "ilaios.skill.media.generation-proposal.v1",
        "media.generate",
        "shot-plan.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.voice-audio.v1",
        "ilaios.skill.media.voice-audio.v1",
        "media.audio",
        "script.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.editor.v1",
        "ilaios.skill.media.edit-proposal.v1",
        "media.assemble",
        "asset.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.qa.v1",
        "ilaios.skill.media.qa-proposal.v1",
        "media.verify",
        "artifact.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.social-metadata.v1",
        "ilaios.skill.media.social-metadata.v1",
        "social.metadata",
        "artifact.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.media.publishing.v1",
        "ilaios.skill.media.publishing-proposal.v1",
        "social.publish-propose",
        "artifact.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.intelligence.research.v1",
        "ilaios-research",
        "research.collect",
        "source.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.intelligence.fact-check.v1",
        "ilaios-source-validation",
        "research.verify",
        "source.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.intelligence.data-analyst.v1",
        "ilaios.skill.intelligence.data-analyst.v1",
        "data.analyze",
        "data.read",
    ),
    MediaIntelligenceAgentBinding(
        "ilaios.agent.intelligence.knowledge.v1",
        "ilaios-research-synthesis",
        "knowledge.curate",
        "evidence.read",
    ),
)

_BINDINGS_BY_ID = {item.agent_id: item for item in MEDIA_INTELLIGENCE_AGENT_BINDINGS}
MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES = frozenset(
    item.capability for item in MEDIA_INTELLIGENCE_AGENT_BINDINGS
)


@dataclass(frozen=True, slots=True)
class MediaIntelligenceProviderBackedAgentRequest:
    invocation: AgentInvocation
    grant: ExecutionGrant
    tenant_id: str
    scopes: tuple[Scope, ...]
    prompt: str
    input_tokens: int
    max_output_tokens: int
    now: datetime


@dataclass(frozen=True, slots=True)
class MediaIntelligenceProviderBackedAgentResult:
    execution: NamedAgentExecution
    model_id: str
    provider_id: str
    evidence_digest: str


class MediaIntelligenceProviderBackedExecutor:
    """Execute bounded Media/Intelligence proposals on the canonical runtime."""

    def __init__(
        self,
        named_executor: NamedAgentExecutor,
        provider_adapter: GovernedAIProviderAdapter,
    ) -> None:
        self._named = named_executor
        self._providers = provider_adapter

    def execute(
        self,
        request: MediaIntelligenceProviderBackedAgentRequest,
    ) -> MediaIntelligenceProviderBackedAgentResult:
        binding = media_intelligence_binding_for(request.invocation.target_id)
        if binding.execution_mode != "governed-ai":
            raise MediaIntelligenceAgentExecutionError(
                "Media/Intelligence binding is not provider-backed"
            )
        if request.invocation.capability != binding.capability:
            raise MediaIntelligenceAgentExecutionError(
                "invocation capability diverges from Media/Intelligence binding"
            )
        if request.invocation.permission != binding.permission:
            raise MediaIntelligenceAgentExecutionError(
                "invocation permission diverges from Media/Intelligence binding"
            )
        if request.prompt != request.invocation.prompt:
            raise MediaIntelligenceAgentExecutionError(
                "provider prompt must equal admitted invocation prompt"
            )
        if not request.invocation.external_egress or not request.invocation.dlp_approved:
            raise MediaIntelligenceAgentExecutionError(
                "external AI execution requires explicit egress and DLP approval"
            )
        if request.now.tzinfo is None:
            raise MediaIntelligenceAgentExecutionError(
                "execution timestamp must be timezone-aware"
            )
        if request.input_tokens < 0 or request.max_output_tokens <= 0:
            raise MediaIntelligenceAgentExecutionError("token estimates must be bounded")

        denied_models: set[str] = set()
        last_error: Exception | None = None
        while True:
            try:
                selection = self._providers.select(
                    binding.capability,
                    denied_models=frozenset(denied_models),
                )
            except GovernanceError as exc:
                raise MediaIntelligenceAgentExecutionError(
                    "no governed Media/Intelligence AI fallback remains"
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
                raise MediaIntelligenceAgentExecutionError(
                    "AI provider credential, permission, or billing gate failed"
                ) from exc
            except (AIProviderError, GovernanceError, RuntimeRoutingError) as exc:
                denied_models.add(selection.model_id)
                last_error = exc
                continue

            output = execution.route.get("output")
            if not isinstance(output, dict):
                raise MediaIntelligenceAgentExecutionError(
                    "provider output evidence is missing"
                )
            if output.get("model_id") != selection.model_id:
                raise MediaIntelligenceAgentExecutionError(
                    "persisted model identity diverged from selection"
                )
            if output.get("provider_id") != selection.provider_id:
                raise MediaIntelligenceAgentExecutionError(
                    "persisted provider identity diverged from selection"
                )
            return MediaIntelligenceProviderBackedAgentResult(
                execution=execution,
                model_id=selection.model_id,
                provider_id=selection.provider_id,
                evidence_digest=execution_evidence_digest(execution),
            )


def media_intelligence_binding_for(agent_id: str) -> MediaIntelligenceAgentBinding:
    try:
        return _BINDINGS_BY_ID[agent_id]
    except KeyError as exc:
        raise MediaIntelligenceAgentExecutionError(
            "agent is outside Media/Intelligence execution bindings"
        ) from exc


def validate_media_intelligence_agent_bindings() -> None:
    expected_ids = {
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team in {"media", "intelligence"}
    }
    configured_ids = set(_BINDINGS_BY_ID)
    if configured_ids != expected_ids:
        raise MediaIntelligenceAgentExecutionError(
            "Media/Intelligence binding coverage mismatch "
            f"missing={sorted(expected_ids-configured_ids)} "
            f"extra={sorted(configured_ids-expected_ids)}"
        )
    if len(MEDIA_INTELLIGENCE_AGENT_BINDINGS) != 12:
        raise MediaIntelligenceAgentExecutionError(
            "Media/Intelligence execution population must be twelve"
        )
    for binding in MEDIA_INTELLIGENCE_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        if binding.capability not in manifest.capabilities:
            raise MediaIntelligenceAgentExecutionError(
                f"binding capability exceeds manifest: {binding.agent_id}"
            )
        if binding.permission not in manifest.permissions:
            raise MediaIntelligenceAgentExecutionError(
                f"binding permission exceeds manifest: {binding.agent_id}"
            )
        if binding.execution_mode != "governed-ai":
            raise MediaIntelligenceAgentExecutionError(
                "Media/Intelligence agents must remain proposal-only governed AI"
            )
    publishing = media_intelligence_binding_for("ilaios.agent.media.publishing.v1")
    if publishing.capability != "social.publish-propose":
        raise MediaIntelligenceAgentExecutionError(
            "Publishing agent must not receive direct social.publish authority"
        )


validate_media_intelligence_agent_bindings()
