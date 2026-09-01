"""SF-10 governed Software Factory handoff into specialized factory boundaries.

This adapter reuses the existing first-party Research/Data, Security,
Creative/Document, Commerce/Growth, and Personal Operations factories. It
transfers typed intent and evidence only; no approval, independent-verification,
external-mutation, deployment, spend, or account authority propagates from the
Software Factory.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from services.capability_registry import capability
from services.commerce_growth_factory import CommerceGrowthFactory
from services.control_plane.proposals import GoalSpec
from services.creative_document_factory import CreativeDocumentFactory
from services.personal_operations_factory import PersonalOperationsFactory
from services.research_data_factory import ResearchDataFactory
from services.security_factory import SecurityFactory, SecurityScope
from services.software_factory import PromotionProposal, SoftwareFactoryError
from services.software_factory_agents import EngineeringAgentExecution

SOURCE_CAPABILITY = "ilaios.capability.software-factory"
RESEARCH_DATA_CAPABILITY = "ilaios.capability.research-data"
SECURITY_CAPABILITY = "ilaios.capability.security-factory"
CREATIVE_DOCUMENT_CAPABILITY = "ilaios.capability.creative-document"
COMMERCE_GROWTH_CAPABILITY = "ilaios.capability.commerce-growth"
PERSONAL_OPERATIONS_CAPABILITY = "ilaios.capability.personal-operations"
SPECIALIZED_TARGETS = frozenset(
    {
        RESEARCH_DATA_CAPABILITY,
        SECURITY_CAPABILITY,
        CREATIVE_DOCUMENT_CAPABILITY,
        COMMERCE_GROWTH_CAPABILITY,
        PERSONAL_OPERATIONS_CAPABILITY,
    }
)

_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HANDOFF_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class SpecializedFactoryHandoffError(SoftwareFactoryError):
    """An SF-10 specialized-factory invariant failed closed."""


@dataclass(frozen=True, slots=True)
class FactorySourceInput:
    """Content-addressed source material handed to a bounded target factory."""

    source_id: str
    locator: str
    content: bytes
    trusted: bool


@dataclass(frozen=True, slots=True)
class ResearchDataPayload:
    claim_id: str
    statement: str
    sources: tuple[FactorySourceInput, ...]


@dataclass(frozen=True, slots=True)
class SecurityPayload:
    scope_id: str
    repository_root: Path


@dataclass(frozen=True, slots=True)
class CreativeDocumentPayload:
    artifact_id: str
    title: str
    sections: tuple[str, ...]
    sources: tuple[FactorySourceInput, ...]


@dataclass(frozen=True, slots=True)
class CommerceGrowthPayload:
    plan_id: str
    audience: str
    channels: tuple[str, ...]
    sources: tuple[FactorySourceInput, ...]


@dataclass(frozen=True, slots=True)
class PersonalOperationsPayload:
    plan_id: str
    steps: tuple[tuple[str, str, str, str], ...]


SpecializedPayload: TypeAlias = (
    ResearchDataPayload
    | SecurityPayload
    | CreativeDocumentPayload
    | CommerceGrowthPayload
    | PersonalOperationsPayload
)


@dataclass(frozen=True, slots=True)
class SpecializedFactoryHandoffRequest:
    """Typed cross-factory request carrying evidence but no inherited authority."""

    handoff_id: str
    goal: GoalSpec
    software_proposal: PromotionProposal
    engineering_execution: EngineeringAgentExecution
    target_capability: str
    payload: SpecializedPayload


@dataclass(frozen=True, slots=True)
class SpecializedFactoryHandoffArtifact:
    """Immutable evidence linking a Software Factory proposal to a target object."""

    handoff_id: str
    source_capability: str
    target_capability: str
    goal_sha256: str
    software_proposal_id: str
    software_job_id: str
    software_evidence_id: str
    repository_sha: str
    engineering_agent_id: str
    engineering_verifier_id: str
    engineering_execution_sha256: str
    target_object_id: str
    target_output_sha256: str
    target_status: str
    target_approved: bool
    independent_verification_completed: bool
    authority_propagated: bool
    external_applied: bool
    artifact_sha256: str


@dataclass(frozen=True, slots=True)
class _TargetResult:
    object_id: str
    output_sha256: str
    status: str


class SoftwareToSpecializedFactoryHandoff:
    """Dispatch governed Software Factory evidence into existing specialized factories."""

    def __init__(
        self,
        research_data: ResearchDataFactory,
        security: SecurityFactory,
        creative_document: CreativeDocumentFactory,
        commerce_growth: CommerceGrowthFactory,
        personal_operations: PersonalOperationsFactory,
    ) -> None:
        self._research_data = research_data
        self._security = security
        self._creative_document = creative_document
        self._commerce_growth = commerce_growth
        self._personal_operations = personal_operations
        self._artifacts: dict[str, SpecializedFactoryHandoffArtifact] = {}
        _validate_target_registry()

    def create(
        self, request: SpecializedFactoryHandoffRequest
    ) -> SpecializedFactoryHandoffArtifact:
        _validate_handoff_id(request.handoff_id)
        if request.handoff_id in self._artifacts:
            raise SpecializedFactoryHandoffError("handoff_id already exists")
        _validate_source_evidence(request.software_proposal, request.engineering_execution)
        if request.target_capability not in SPECIALIZED_TARGETS:
            raise SpecializedFactoryHandoffError(
                "target capability is not an SF-10 specialized factory"
            )

        target = self._dispatch(request)
        proposal = request.software_proposal
        execution = request.engineering_execution
        evidence = proposal.evidence
        goal_sha256 = _goal_digest(request.goal)
        material = {
            "handoff_id": request.handoff_id,
            "source_capability": SOURCE_CAPABILITY,
            "target_capability": request.target_capability,
            "goal_sha256": goal_sha256,
            "acceptance_criteria": list(request.goal.acceptance_criteria),
            "software_proposal_id": proposal.proposal_id,
            "software_job_id": proposal.job_id,
            "software_evidence_id": evidence.evidence_id,
            "repository_sha": evidence.repository_sha,
            "engineering_agent_id": execution.admission.agent_id,
            "engineering_verifier_id": execution.verifier_id,
            "engineering_execution_sha256": execution.evidence_digest,
            "target_object_id": target.object_id,
            "target_output_sha256": target.output_sha256,
            "target_status": target.status,
            "target_approved": False,
            "independent_verification_completed": False,
            "authority_propagated": False,
            "external_applied": False,
        }
        artifact_sha256 = _digest(material)
        artifact = SpecializedFactoryHandoffArtifact(
            handoff_id=request.handoff_id,
            source_capability=SOURCE_CAPABILITY,
            target_capability=request.target_capability,
            goal_sha256=goal_sha256,
            software_proposal_id=proposal.proposal_id,
            software_job_id=proposal.job_id,
            software_evidence_id=evidence.evidence_id,
            repository_sha=evidence.repository_sha,
            engineering_agent_id=execution.admission.agent_id,
            engineering_verifier_id=execution.verifier_id,
            engineering_execution_sha256=execution.evidence_digest,
            target_object_id=target.object_id,
            target_output_sha256=target.output_sha256,
            target_status=target.status,
            target_approved=False,
            independent_verification_completed=False,
            authority_propagated=False,
            external_applied=False,
            artifact_sha256=artifact_sha256,
        )
        self._artifacts[request.handoff_id] = artifact
        return artifact

    def artifact(self, handoff_id: str) -> SpecializedFactoryHandoffArtifact:
        artifact = self._artifacts.get(handoff_id)
        if artifact is None:
            raise SpecializedFactoryHandoffError("handoff artifact does not exist")
        return artifact

    def _dispatch(self, request: SpecializedFactoryHandoffRequest) -> _TargetResult:
        target = request.target_capability
        payload = request.payload
        if target == RESEARCH_DATA_CAPABILITY:
            if not isinstance(payload, ResearchDataPayload):
                raise SpecializedFactoryHandoffError("research/data payload type mismatch")
            return self._research(payload)
        if target == SECURITY_CAPABILITY:
            if not isinstance(payload, SecurityPayload):
                raise SpecializedFactoryHandoffError("security payload type mismatch")
            return self._security_scan(payload)
        if target == CREATIVE_DOCUMENT_CAPABILITY:
            if not isinstance(payload, CreativeDocumentPayload):
                raise SpecializedFactoryHandoffError("creative/document payload type mismatch")
            return self._creative(payload)
        if target == COMMERCE_GROWTH_CAPABILITY:
            if not isinstance(payload, CommerceGrowthPayload):
                raise SpecializedFactoryHandoffError("commerce/growth payload type mismatch")
            return self._commerce(request.goal, payload)
        if target == PERSONAL_OPERATIONS_CAPABILITY:
            if not isinstance(payload, PersonalOperationsPayload):
                raise SpecializedFactoryHandoffError("personal-operations payload type mismatch")
            return self._personal(request.goal, payload)
        raise SpecializedFactoryHandoffError("unsupported specialized factory")

    def _research(self, payload: ResearchDataPayload) -> _TargetResult:
        source_ids = self._register_research_sources(payload.sources)
        claim = self._research_data.propose_claim(
            payload.claim_id,
            statement=payload.statement,
            source_ids=source_ids,
        )
        return _TargetResult(
            claim.claim_id,
            _digest(
                {
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "source_ids": list(claim.source_ids),
                    "verified": claim.verified,
                }
            ),
            "REVIEW_REQUIRED",
        )

    def _security_scan(self, payload: SecurityPayload) -> _TargetResult:
        scope = SecurityScope(payload.scope_id, payload.repository_root.resolve())
        report = self._security.scan_repository(scope)
        findings = [
            {
                "finding_id": item.finding_id,
                "category": item.category,
                "severity": int(item.severity),
                "location": item.location,
                "line": item.line,
                "message": item.message,
                "remediation": item.remediation,
            }
            for item in report.findings
        ]
        return _TargetResult(
            report.scope_id,
            _digest(
                {
                    "scope_id": report.scope_id,
                    "passed": report.passed,
                    "findings": findings,
                }
            ),
            "REVIEW_REQUIRED" if report.passed else "BLOCKED",
        )

    def _creative(self, payload: CreativeDocumentPayload) -> _TargetResult:
        source_ids = self._register_creative_sources(payload.sources)
        artifact = self._creative_document.compose(
            payload.artifact_id,
            title=payload.title,
            sections=payload.sections,
            source_ids=source_ids,
        )
        return _TargetResult(
            artifact.artifact_id,
            _digest(
                {
                    "artifact_id": artifact.artifact_id,
                    "title": artifact.title,
                    "body_sha256": artifact.body_sha256,
                    "source_ids": list(artifact.source_ids),
                    "approved": artifact.approved,
                }
            ),
            "REVIEW_REQUIRED",
        )

    def _commerce(
        self, goal: GoalSpec, payload: CommerceGrowthPayload
    ) -> _TargetResult:
        source_ids = self._register_commerce_sources(payload.sources)
        plan = self._commerce_growth.propose(
            payload.plan_id,
            objective=goal.objective,
            audience=payload.audience,
            channels=payload.channels,
            source_ids=source_ids,
            paid_spend_cents=0,
        )
        return _TargetResult(plan.plan_id, plan.plan_sha256, "REVIEW_REQUIRED")

    def _personal(
        self, goal: GoalSpec, payload: PersonalOperationsPayload
    ) -> _TargetResult:
        plan = self._personal_operations.propose(
            payload.plan_id,
            objective=goal.objective,
            steps=payload.steps,
        )
        return _TargetResult(plan.plan_id, plan.plan_sha256, "REVIEW_REQUIRED")

    def _register_research_sources(
        self, sources: tuple[FactorySourceInput, ...]
    ) -> tuple[str, ...]:
        _validate_sources(sources)
        for source in sources:
            self._research_data.register_source(
                source.source_id,
                locator=source.locator,
                content=source.content,
                trusted=source.trusted,
            )
        return tuple(source.source_id for source in sources)

    def _register_creative_sources(
        self, sources: tuple[FactorySourceInput, ...]
    ) -> tuple[str, ...]:
        _validate_sources(sources)
        for source in sources:
            self._creative_document.register_source(
                source.source_id,
                locator=source.locator,
                content=source.content,
                trusted=source.trusted,
            )
        return tuple(source.source_id for source in sources)

    def _register_commerce_sources(
        self, sources: tuple[FactorySourceInput, ...]
    ) -> tuple[str, ...]:
        _validate_sources(sources)
        for source in sources:
            self._commerce_growth.register_source(
                source.source_id,
                locator=source.locator,
                content=source.content,
                trusted=source.trusted,
            )
        return tuple(source.source_id for source in sources)


def _validate_target_registry() -> None:
    for capability_id in SPECIALIZED_TARGETS:
        definition = capability(capability_id)
        if definition.domain != "factory":
            raise SpecializedFactoryHandoffError(
                "SF-10 target must resolve to the canonical factory domain"
            )


def _validate_source_evidence(
    proposal: PromotionProposal, execution: EngineeringAgentExecution
) -> None:
    evidence = proposal.evidence
    if not proposal.requires_human_approval:
        raise SpecializedFactoryHandoffError(
            "Software Factory proposal must preserve human approval requirement"
        )
    if proposal.production_applied:
        raise SpecializedFactoryHandoffError(
            "production-applied Software Factory output cannot enter SF-10"
        )
    if not evidence.validation.passed:
        raise SpecializedFactoryHandoffError(
            "Software Factory validation must pass before specialized handoff"
        )
    if _SHA1.fullmatch(evidence.repository_sha) is None:
        raise SpecializedFactoryHandoffError("Software Factory repository SHA is invalid")

    agent_id = execution.admission.agent_id
    if not agent_id.startswith("ilaios.agent.engineering."):
        raise SpecializedFactoryHandoffError(
            "SF-10 accepts only canonical engineering-agent execution evidence"
        )
    if execution.verifier_id == agent_id:
        raise SpecializedFactoryHandoffError(
            "engineering producer cannot independently verify its own handoff"
        )
    if _SHA256.fullmatch(execution.evidence_digest) is None:
        raise SpecializedFactoryHandoffError(
            "engineering execution evidence digest is invalid"
        )
    if execution.status not in {"READY", "REVIEW_REQUIRED"}:
        raise SpecializedFactoryHandoffError("engineering execution is not handoff-eligible")
    if not execution.skill_results:
        raise SpecializedFactoryHandoffError(
            "engineering execution must contain SF-7 skill evidence"
        )
    if any(result.status != "READY" for result in execution.skill_results):
        raise SpecializedFactoryHandoffError(
            "all SF-7 skill steps must be READY for specialized handoff"
        )


def _validate_handoff_id(handoff_id: str) -> None:
    if _HANDOFF_ID.fullmatch(handoff_id) is None:
        raise SpecializedFactoryHandoffError(
            "handoff_id must be a bounded canonical identifier"
        )


def _validate_sources(sources: tuple[FactorySourceInput, ...]) -> None:
    if not sources:
        raise SpecializedFactoryHandoffError("specialized source set must not be empty")
    source_ids = tuple(source.source_id for source in sources)
    if len(source_ids) != len(set(source_ids)):
        raise SpecializedFactoryHandoffError("specialized source IDs must be unique")
    for source in sources:
        if not source.source_id or source.source_id != source.source_id.strip():
            raise SpecializedFactoryHandoffError("specialized source ID must be trimmed")
        if not source.locator.strip() or not source.content:
            raise SpecializedFactoryHandoffError(
                "specialized source requires locator and content"
            )


def _goal_digest(goal: GoalSpec) -> str:
    return _digest(
        {
            "objective": goal.objective,
            "acceptance_criteria": list(goal.acceptance_criteria),
            "risk_class": goal.risk_class.value,
            "data_class": goal.data_class.value,
            "budget": {
                "max_attempts": goal.budget.max_attempts,
                "max_runtime_seconds": goal.budget.max_runtime_seconds,
                "max_external_spend_minor": goal.budget.max_external_spend_minor,
            },
        }
    )


def _digest(material: object) -> str:
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
