"""Desktop composition adapter for the governed Assistant conversational runtime.

This module adds no identity, routing, provider, grant, memory, or Knowledge
authority. It reuses the existing authenticated Desktop conversation lifecycle and
only replaces the deterministic response producer for a `send` operation while a
governed Assistant runtime is explicitly composed by the packaged sidecar.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
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
from services.reference_assets import ReferenceAssetStore
from services.source_media import SourceMediaStore


_ACTIVE_ASSISTANT: ContextVar[
    tuple[AssistantConversationRuntime, str, str] | None
] = ContextVar("ilaios_desktop_assistant_runtime", default=None)
_ORIGINAL_GUIDANCE = _identity_core._assistant_guidance


def _governed_assistant_guidance(text: str, locale: str) -> dict[str, object]:
    active = _ACTIVE_ASSISTANT.get()
    if active is None:
        return _ORIGINAL_GUIDANCE(text, locale)
    runtime, tenant_id, request_id = active
    result = runtime.complete(
        text=text,
        locale=locale,
        tenant_id=tenant_id,
        request_id=request_id,
        now=datetime.now(timezone.utc),
    )
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
        conversation_id = body.get("conversation_id")
        message_id = body.get("message_id")
        if not isinstance(conversation_id, str) or not isinstance(message_id, str):
            super()._assistant_operation(body)
            return
        request_id = f"desktop-assistant:{conversation_id}:{message_id}"
        token = _ACTIVE_ASSISTANT.set((runtime, session.tenant_id, request_id))
        try:
            super()._assistant_operation(body)
        finally:
            _ACTIVE_ASSISTANT.reset(token)


__all__ = [
    "AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer",
    "AssistantRuntimeCompanyKnowledgeDesktopIdentityRequestHandler",
]
