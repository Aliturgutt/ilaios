"""Desktop composition adapter for the governed Assistant conversational runtime.

This module adds no identity, routing, provider, grant, memory, or Knowledge
authority. It reuses the existing authenticated Desktop conversation lifecycle and
only replaces the deterministic response producer for a `send` operation while a
governed Assistant runtime is explicitly composed by the packaged sidecar.
"""

from __future__ import annotations

import secrets
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

from services import desktop_identity_server_core as _identity_core
from services.assistant_conversation_runtime import (
    AssistantConversationError,
    AssistantConversationRuntime,
)
from services.company_knowledge_desktop import (
    CompanyKnowledgeDesktopIdentityHTTPServer,
    CompanyKnowledgeDesktopIdentityRequestHandler,
    TenantCompanyKnowledgeRegistry,
)
from services.desktop_oidc import DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator
from services.knowledge_runtime import KnowledgeRuntimeError
from services.reference_assets import ReferenceAssetStore
from services.runtime import BlastRadiusBudget, DurableGrantPolicy, ExecutionGrant
from services.runtime.grants import GrantError
from services.source_media import SourceMediaStore


_ASSISTANT_KNOWLEDGE_ACTION = "knowledge.retrieve"


@dataclass(frozen=True, slots=True)
class _AssistantRequestContext:
    runtime: AssistantConversationRuntime
    grants: DurableGrantPolicy
    company_knowledge: TenantCompanyKnowledgeRegistry
    principal_id: str
    tenant_id: str
    workload_id: str
    request_id: str


_ACTIVE_ASSISTANT: ContextVar[_AssistantRequestContext | None] = ContextVar(
    "ilaios_desktop_assistant_runtime", default=None
)
_ORIGINAL_GUIDANCE = _identity_core._assistant_guidance


def _knowledge_resource(tenant_id: str, project_id: str, workload_id: str) -> str:
    return f"knowledge:{tenant_id}:{project_id}:{workload_id}"


def _governed_assistant_guidance(text: str, locale: str) -> dict[str, object]:
    active = _ACTIVE_ASSISTANT.get()
    if active is None:
        return _ORIGINAL_GUIDANCE(text, locale)

    now = datetime.now(timezone.utc)
    try:
        knowledge = active.company_knowledge.runtime_for(active.tenant_id)
        project_id = knowledge.project_id
        authorized_context: dict[str, object] | None = None
        state = knowledge.state()
        metrics = state.get("metrics")
        if not isinstance(metrics, dict):
            raise AssistantConversationError("Assistant Knowledge state is malformed")
        active_units = metrics.get("active_units")
        if not isinstance(active_units, int) or isinstance(active_units, bool) or active_units < 0:
            raise AssistantConversationError("Assistant Knowledge state is malformed")
        if active_units:
            resource = _knowledge_resource(
                active.tenant_id,
                project_id,
                active.workload_id,
            )
            human_grant = ExecutionGrant(
                grant_id=f"assistant-knowledge-{secrets.token_hex(16)}",
                subject_id=active.principal_id,
                actions=frozenset({_ASSISTANT_KNOWLEDGE_ACTION}),
                resources=frozenset({resource}),
                expires_at=now + timedelta(minutes=5),
                budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
            )
            active.grants.register(human_grant)
            try:
                active.grants.authorize(
                    human_grant,
                    subject_id=active.principal_id,
                    action=_ASSISTANT_KNOWLEDGE_ACTION,
                    resource=resource,
                    now=now,
                )
                authorized_context = knowledge.retrieve(
                    retrieval_id=(
                        f"{active.request_id}-knowledge-{secrets.token_hex(8)}"
                    ),
                    query=text,
                    purpose="company-context",
                    top_k=5,
                    candidate_limit=20,
                    max_context_chars=6000,
                )
                if authorized_context.get("tenant_id") != active.tenant_id:
                    raise AssistantConversationError("Assistant Knowledge tenant mismatch")
                if authorized_context.get("project_id") != project_id:
                    raise AssistantConversationError("Assistant Knowledge project mismatch")
            finally:
                active.grants.revoke(human_grant.grant_id, now=now)

        result = active.runtime.complete(
            text=text,
            locale=locale,
            principal_id=active.principal_id,
            tenant_id=active.tenant_id,
            project_id=project_id,
            workload_id=active.workload_id,
            request_id=active.request_id,
            now=now,
            authorized_context=authorized_context,
        )
    except (GrantError, KnowledgeRuntimeError) as error:
        raise AssistantConversationError("Assistant Knowledge authorization unavailable") from error

    observed_at = datetime.now(timezone.utc).isoformat()
    return {
        "text": result.text,
        "status": "GUIDANCE",
        "provenance": [
            {
                "source_id": f"governed-model:{result.model_id}",
                "visibility": "GOVERNED_MODEL",
                "source_version": result.evidence_digest,
                "observed_at": observed_at,
                "evidence_id": result.evidence_digest,
                "freshness": "LIVE_EXECUTION",
            }
        ],
        "response_class": "MODEL_RESPONSE",
        "live": True,
        "proposed_action": None,
        "confirmation_required": False,
        "cost_state": "ZERO_VERIFIED",
        "approval_state": "NOT_REQUESTED",
        "model_status": "GOVERNED_ZERO_COST",
    }


# The existing core conversation method resolves this module-level callable in
# its defining module. Install one process-wide dispatcher, but keep the actual
# runtime/request scope in ContextVar so concurrent Desktop requests cannot
# substitute another tenant's runtime context.
if _identity_core._assistant_guidance is not _governed_assistant_guidance:
    _identity_core._assistant_guidance = _governed_assistant_guidance


class AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer(
    CompanyKnowledgeDesktopIdentityHTTPServer
):
    """Existing packaged Desktop server with an explicit governed chat runtime."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore,
        company_knowledge: TenantCompanyKnowledgeRegistry,
        grants: DurableGrantPolicy,
        assistant_runtime: AssistantConversationRuntime | None,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
            reference_assets=reference_assets,
            source_media=source_media,
            company_knowledge=company_knowledge,
        )
        self.grants = grants
        self.assistant_runtime = assistant_runtime
        self.RequestHandlerClass = AssistantRuntimeCompanyKnowledgeDesktopIdentityRequestHandler


class AssistantRuntimeCompanyKnowledgeDesktopIdentityRequestHandler(
    CompanyKnowledgeDesktopIdentityRequestHandler
):
    server: AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer

    def _assistant(self, body: dict[str, Any]) -> None:
        try:
            super()._assistant(body)
        except AssistantConversationError:
            self._send_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Assistant governed model unavailable",
            )

    def _assistant_operation(self, body: dict[str, Any]) -> None:
        runtime = self.server.assistant_runtime
        if body.get("operation") != "send" or runtime is None:
            super()._assistant_operation(body)
            return
        session = self._authenticated_session()
        identity = self._require_identity()
        if identity.is_li_founder_session(session.session_id):
            # Founder-only Li remains a separate persona/memory boundary. Never
            # inject its session into the normal governed Assistant model path.
            super()._assistant_operation(body)
            return
        conversation_id = body.get("conversation_id")
        message_id = body.get("message_id")
        if not isinstance(conversation_id, str) or not isinstance(message_id, str):
            super()._assistant_operation(body)
            return
        request_id = f"desktop-assistant:{conversation_id}:{message_id}"
        workload_id = f"assistant-conversation:{conversation_id}"
        token = _ACTIVE_ASSISTANT.set(
            _AssistantRequestContext(
                runtime=runtime,
                grants=self.server.grants,
                company_knowledge=self.server.company_knowledge,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                workload_id=workload_id,
                request_id=request_id,
            )
        )
        try:
            super()._assistant_operation(body)
        finally:
            _ACTIVE_ASSISTANT.reset(token)


__all__ = [
    "AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer",
    "AssistantRuntimeCompanyKnowledgeDesktopIdentityRequestHandler",
]
