"""Governed agent manifests, permission firewall, and AI security admission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class GrantAuthorizer(Protocol):
    """Minimal execution-grant port required by the permission firewall."""

    def authorize(
        self,
        grant: Any,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None: ...


class AgentSecurityError(PermissionError):
    """Agent invocation failed closed."""


class AgentStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class AgentManifest:
    agent_id: str
    alias: str
    role: str
    team: str
    capabilities: frozenset[str]
    permissions: frozenset[str]
    inputs: frozenset[str]
    outputs: frozenset[str]
    dependencies: frozenset[str]
    allowed_callers: frozenset[str]
    allowed_targets: frozenset[str]
    escalation_path: str
    verifier_id: str
    version: str
    status: AgentStatus

    def __post_init__(self) -> None:
        required = (
            self.agent_id,
            self.alias,
            self.role,
            self.team,
            self.escalation_path,
            self.verifier_id,
            self.version,
        )
        if not all(required):
            raise ValueError("complete stable agent identity and governance metadata required")
        if self.agent_id == self.alias:
            raise ValueError("machine agent ID and human-readable alias must differ")
        if self.agent_id == self.verifier_id:
            raise ValueError("agent cannot independently verify itself")


@dataclass(frozen=True, slots=True)
class AgentInvocation:
    invocation_id: str
    caller_id: str
    target_id: str
    capability: str
    permission: str
    input_class: str
    requested_output_class: str
    prompt: str
    contains_secret: bool = False
    external_egress: bool = False
    dlp_approved: bool = False
    security_scan_passed: bool = False


@dataclass(frozen=True, slots=True)
class AgentAdmissionEvidence:
    invocation_id: str
    agent_id: str
    verifier_id: str
    admitted_at: datetime
    security_scan_passed: bool
    dlp_approved: bool


class PermissionFirewall:
    """Deterministic checks precede every agent execution or target call."""

    _injection_markers = (
        "ignore previous instructions",
        "reveal system prompt",
        "bypass policy",
        "disable security",
        "exfiltrate",
    )

    def __init__(
        self, manifests: tuple[AgentManifest, ...], grants: GrantAuthorizer
    ) -> None:
        self._manifests = {manifest.agent_id: manifest for manifest in manifests}
        self._grants = grants

    def admit(
        self, invocation: AgentInvocation, grant: Any, now: datetime
    ) -> AgentAdmissionEvidence:
        manifest = self._manifests.get(invocation.target_id)
        if manifest is None or manifest.status is not AgentStatus.ACTIVE:
            raise AgentSecurityError("target agent is unavailable")
        if invocation.caller_id not in manifest.allowed_callers:
            raise AgentSecurityError("caller is not allowed")
        if invocation.target_id not in manifest.allowed_targets:
            raise AgentSecurityError("target is not allowed")
        if invocation.capability not in manifest.capabilities:
            raise AgentSecurityError("capability is not allowed")
        if invocation.permission not in manifest.permissions:
            raise AgentSecurityError("permission is not allowed")
        if invocation.input_class not in manifest.inputs:
            raise AgentSecurityError("input class is not allowed")
        if invocation.requested_output_class not in manifest.outputs:
            raise AgentSecurityError("output class is not allowed")
        prompt = invocation.prompt.casefold()
        if any(marker in prompt for marker in self._injection_markers):
            raise AgentSecurityError("prompt injection detected")
        if invocation.contains_secret:
            raise AgentSecurityError("secret-bearing agent input is prohibited")
        if invocation.external_egress and not invocation.dlp_approved:
            raise AgentSecurityError("external egress requires DLP approval")
        if not invocation.security_scan_passed:
            raise AgentSecurityError("independent security scan is required")
        try:
            self._grants.authorize(
                grant,
                subject_id=manifest.agent_id,
                action=invocation.permission,
                resource=invocation.target_id,
                now=now,
            )
        except PermissionError as exc:
            raise AgentSecurityError("execution grant denied invocation") from exc
        return AgentAdmissionEvidence(
            invocation.invocation_id,
            manifest.agent_id,
            manifest.verifier_id,
            now,
            invocation.security_scan_passed,
            invocation.dlp_approved,
        )
