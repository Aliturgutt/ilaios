"""Canonical named-agent bridge into the existing governed runtime.

This module does not create a second agent engine. It binds canonical ILAIOS
agent manifests to the existing permission firewall, scoped execution grants,
immutable skill registry, governed provider routing, and persisted runtime
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.agent_governance import (
    AgentAdmissionEvidence,
    AgentInvocation,
    AgentSecurityError,
    GrantAuthorizer,
    PermissionFirewall,
)
from services.agent_registry import CANONICAL_AGENT_REGISTRY, registration_for
from services.runtime import ExecutionGrant, GovernedRuntime


class NamedAgentExecutionError(RuntimeError):
    """Canonical named-agent execution violated a bridge invariant."""


def provision_canonical_agent(runtime: GovernedRuntime, agent_id: str) -> bool:
    """Provision one registry-backed identity without caller-supplied authority."""
    try:
        registration = registration_for(agent_id)
    except KeyError as exc:
        raise NamedAgentExecutionError("unknown canonical agent identity") from exc
    return runtime.ensure_agent(
        registration.manifest.agent_id, registration.manifest.capabilities
    )


@dataclass(frozen=True, slots=True)
class NamedAgentExecution:
    admission: AgentAdmissionEvidence
    route: dict[str, Any]

    @property
    def verifier_id(self) -> str:
        return self.admission.verifier_id


class NamedAgentExecutor:
    """Bind canonical named agents to the existing governed runtime."""

    def __init__(self, runtime: GovernedRuntime, grants: GrantAuthorizer) -> None:
        self._runtime = runtime
        self._firewall = PermissionFirewall(
            tuple(item.manifest for item in CANONICAL_AGENT_REGISTRY), grants
        )

    def provision_agent(self, agent_id: str) -> bool:
        return provision_canonical_agent(self._runtime, agent_id)

    def ensure_agent(self, agent_id: str) -> bool:
        return provision_canonical_agent(self._runtime, agent_id)

    def provision_skill(
        self, skill_id: str, content: bytes, authorities: frozenset[str]
    ) -> str:
        return self._runtime.register_skill(skill_id, content, authorities)

    def ensure_skill(
        self, skill_id: str, content: bytes, authorities: frozenset[str]
    ) -> str:
        return self._runtime.ensure_skill(skill_id, content, authorities)

    def provision_provider(
        self,
        provider_id: str,
        capabilities: frozenset[str],
        *,
        adapter_kind: str,
        deterministic: bool | None = None,
    ) -> None:
        self._runtime.register_provider(
            provider_id,
            capabilities,
            adapter_kind=adapter_kind,
            deterministic=deterministic,
        )

    def ensure_provider(
        self,
        provider_id: str,
        capabilities: frozenset[str],
        *,
        adapter_kind: str,
        deterministic: bool | None = None,
    ) -> bool:
        return self._runtime.ensure_provider(
            provider_id,
            capabilities,
            adapter_kind=adapter_kind,
            deterministic=deterministic,
        )

    def execute(
        self,
        invocation: AgentInvocation,
        grant: ExecutionGrant,
        *,
        skill_id: str,
        payload: dict[str, Any],
        now: datetime,
        preferred_provider_id: str | None = None,
    ) -> NamedAgentExecution:
        """Admit, route, execute, and bind the result to independent verification."""
        try:
            registration = registration_for(invocation.target_id)
        except KeyError as exc:
            raise AgentSecurityError("target agent is unavailable") from exc
        admission = self._firewall.admit(invocation, grant, now)
        route = self._runtime.execute(
            registration.manifest.agent_id,
            skill_id,
            invocation.capability,
            payload,
            preferred_provider_id=preferred_provider_id,
        )
        if route.get("agent_id") != admission.agent_id:
            raise NamedAgentExecutionError("runtime route identity diverged from admission")
        if admission.verifier_id == admission.agent_id:
            raise NamedAgentExecutionError("producer cannot independently verify itself")
        return NamedAgentExecution(admission, route)

    def routes(self) -> tuple[dict[str, Any], ...]:
        return self._runtime.routes()
