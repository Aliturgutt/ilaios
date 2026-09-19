"""Governed production-runtime bridge for imported open Agent Skills packages.

This module does not create a second runtime, policy engine, approval engine, tool
router, or evidence authority. It composes existing ILAIOS boundaries so that an
imported Agent Skills package can execute only after deterministic tenant/policy
admission, governed runtime approval, Tool Gateway dispatch, and evidence recording.

Bundled scripts remain non-executable here. This bridge executes portable skill
instructions through an already-governed provider adapter; script execution requires
a separately approved first-party tool capability and is intentionally out of scope.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.agent_skills_compat import ImportedAgentSkill, load_agent_skill
from services.cloud import TenantBoundary
from services.governance.runtime import GovernedRuntimeGateway
from services.identity import AccessRequest, AuthorizationEngine, Principal
from services.runtime import GovernedRuntime
from src.core.evidence_chain import EvidenceChain, EvidenceRecord
from src.core.tool_gateway import ToolGateway


class AgentSkillsRuntimeError(PermissionError):
    """Imported skill activation or execution failed closed."""


_EXTERNAL_SKILL_PREFIX = "external.agent-skill"
_TOOL_NAME = "agent-skills.governed-execute"
_POLICY_ACTION = "skill.execute.external"


@dataclass(frozen=True, slots=True)
class ExternalSkillExecutionRequest:
    request_id: str
    principal: Principal
    resource_tenant_id: str
    region: str
    package_root: Path
    expected_package_sha256: str
    agent_id: str
    capability: str
    payload: dict[str, Any]
    risk: str = "high"
    secret_ids: tuple[str, ...] = ()
    approval_id: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.request_id,
            self.principal.principal_id,
            self.principal.tenant_id,
            self.resource_tenant_id,
            self.region,
            self.expected_package_sha256,
            self.agent_id,
            self.capability,
        )
        if not all(value and value == value.strip() for value in required):
            raise ValueError("external skill execution identifiers must be non-blank")
        if self.risk not in {"low", "medium", "high"}:
            raise ValueError("external skill risk must be low, medium, or high")


@dataclass(frozen=True, slots=True)
class ExternalSkillExecutionReceipt:
    request_id: str
    tenant_id: str
    skill_id: str
    package_sha256: str
    capability: str
    provider_id: str
    route_sequence: int
    admission_proven: bool
    approval_proven: bool
    evidence_chain_hash: str
    created_at: str
    output: dict[str, Any]


class AgentSkillsProductionRuntime:
    """Compose existing governance boundaries for imported skill execution."""

    def __init__(
        self,
        *,
        runtime: GovernedRuntime,
        governed_gateway: GovernedRuntimeGateway,
        tool_gateway: ToolGateway,
        authorization: AuthorizationEngine,
        tenants: TenantBoundary,
        evidence_chain: EvidenceChain,
    ) -> None:
        self._runtime = runtime
        self._governed_gateway = governed_gateway
        self._tool_gateway = tool_gateway
        self._authorization = authorization
        self._tenants = tenants
        self._evidence_chain = evidence_chain
        self._tool_gateway.register_handler(_TOOL_NAME, self._governed_gateway.execute)

    def submit(self, request: ExternalSkillExecutionRequest, *, now: datetime) -> dict[str, object]:
        """Authorize tenant/policy scope, freeze immutable skill content, and admit work."""
        if now.tzinfo is None:
            raise AgentSkillsRuntimeError("execution time must be timezone-aware")
        if request.principal.tenant_id != request.resource_tenant_id:
            raise AgentSkillsRuntimeError("cross-tenant external skill execution denied")

        self._tenants.authorize(
            request.principal.tenant_id,
            resource_tenant=request.resource_tenant_id,
            region=request.region,
        )
        self._authorization.authorize(
            request.principal,
            AccessRequest(
                tenant_id=request.principal.tenant_id,
                resource_tenant_id=request.resource_tenant_id,
                action=_POLICY_ACTION,
                privileged=request.risk == "high",
                high_risk=False,
                approval_id=request.approval_id,
            ),
            now,
        )

        package = self._load_and_verify(request)
        skill_id = self._skill_id(package)
        # Registration is immutable and capability-bounded. It does not bypass
        # per-request admission or approval enforced below by GovernedRuntimeGateway.
        digest = self._runtime.ensure_skill(
            skill_id,
            package.instructions.encode("utf-8"),
            frozenset({request.capability}),
        )
        if digest != hashlib.sha256(package.instructions.encode("utf-8")).hexdigest():
            raise AgentSkillsRuntimeError("runtime skill digest mismatch")

        admission = self._governed_gateway.submit(
            request.request_id,
            request.principal.principal_id,
            request.agent_id,
            skill_id,
            request.capability,
            request.payload,
            request.secret_ids,
            risk=request.risk,
        )
        return {
            **admission,
            "tenant_id": request.principal.tenant_id,
            "skill_id": skill_id,
            "package_sha256": package.package_sha256,
            "contains_scripts": package.contains_scripts,
            "script_execution_authorized": False,
        }

    def execute(self, request: ExternalSkillExecutionRequest) -> ExternalSkillExecutionReceipt:
        """Execute only through Tool Gateway and append validation evidence."""
        package = self._load_and_verify(request)
        skill_id = self._skill_id(package)
        result = self._tool_gateway.dispatch(_TOOL_NAME, request.request_id)
        if not isinstance(result, dict):
            raise AgentSkillsRuntimeError("governed runtime result must be an object")
        if result.get("skill_id") != skill_id:
            raise AgentSkillsRuntimeError("runtime skill identity mismatch")
        if result.get("capability") != request.capability:
            raise AgentSkillsRuntimeError("runtime capability mismatch")
        sequence = result.get("sequence")
        provider_id = result.get("provider_id")
        if not isinstance(sequence, int) or sequence < 1:
            raise AgentSkillsRuntimeError("runtime route sequence is invalid")
        if not isinstance(provider_id, str) or not provider_id:
            raise AgentSkillsRuntimeError("runtime provider identity is invalid")

        admission = self._governed_gateway.admission_snapshot(request.request_id)
        if not bool(admission["admission_proven"]):
            raise AgentSkillsRuntimeError("governed admission evidence is incomplete")

        output = result.get("output")
        if not isinstance(output, dict):
            raise AgentSkillsRuntimeError("external skill output must be an object")
        created_at = str(result.get("created_at") or "")
        if not created_at:
            raise AgentSkillsRuntimeError("runtime evidence timestamp is missing")

        evidence_payload = {
            "request_id": request.request_id,
            "tenant_id": request.principal.tenant_id,
            "skill_id": skill_id,
            "package_sha256": package.package_sha256,
            "capability": request.capability,
            "provider_id": provider_id,
            "route_sequence": sequence,
            "admission": admission,
            "runtime_created_at": created_at,
            "output_sha256": hashlib.sha256(
                json.dumps(output, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
        data_hash = hashlib.sha256(
            json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        records = self._evidence_chain.get_records()
        record = EvidenceRecord(
            timestamp=datetime.now(timezone.utc),
            source="agent-skills-production-runtime",
            data_hash=data_hash,
            prev_hash=None if not records else records[-1].chain_hash,
        )
        self._evidence_chain.add_record(record)
        if not self._evidence_chain.verify_integrity():
            raise AgentSkillsRuntimeError("evidence chain integrity verification failed")

        return ExternalSkillExecutionReceipt(
            request_id=request.request_id,
            tenant_id=request.principal.tenant_id,
            skill_id=skill_id,
            package_sha256=package.package_sha256,
            capability=request.capability,
            provider_id=provider_id,
            route_sequence=sequence,
            admission_proven=True,
            approval_proven=bool(admission["approval_proven"]),
            evidence_chain_hash=record.chain_hash,
            created_at=created_at,
            output=output,
        )

    def _load_and_verify(self, request: ExternalSkillExecutionRequest) -> ImportedAgentSkill:
        package = load_agent_skill(request.package_root)
        if package.package_sha256 != request.expected_package_sha256:
            raise AgentSkillsRuntimeError("imported skill package digest changed")
        if not package.instructions.strip():
            raise AgentSkillsRuntimeError("imported skill instructions are empty")
        if package.execution_authorized:
            raise AgentSkillsRuntimeError("portable metadata unexpectedly granted execution authority")
        return package

    @staticmethod
    def _skill_id(package: ImportedAgentSkill) -> str:
        return f"{_EXTERNAL_SKILL_PREFIX}.{package.metadata.name}.{package.package_sha256[:16]}"
