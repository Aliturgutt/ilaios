"""Typed SF-9 handoff from Software Factory into the existing App Factory.

The handoff transfers evidence and intent only. It never transfers execution grants,
approvals, client-mutation authority, signing authority, deployment authority, or
store-submission authority. App Factory keeps its own review boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from services.app_factory import AppFactory, AppRequest
from services.control_plane.proposals import GoalSpec
from services.software_factory import PromotionProposal, SoftwareFactoryError
from services.software_factory_agents import EngineeringAgentExecution

SOURCE_CAPABILITY = "ilaios.capability.software-factory"
TARGET_CAPABILITY = "ilaios.capability.app-factory"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HANDOFF_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class AppFactoryHandoffError(SoftwareFactoryError):
    """The Software Factory to App Factory handoff failed closed."""


@dataclass(frozen=True, slots=True)
class AppFactoryHandoffRequest:
    """Typed cross-factory request with no inherited execution authority."""

    handoff_id: str
    goal: GoalSpec
    software_proposal: PromotionProposal
    engineering_execution: EngineeringAgentExecution
    platform: str
    action: str = "client_change_request"


@dataclass(frozen=True, slots=True)
class AppFactoryHandoffArtifact:
    """Immutable evidence linking Software Factory output to an App Factory request."""

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
    app_request_id: str
    app_request_sha256: str
    platform: str
    action: str
    source_review_required: bool
    app_approved_for_review: bool
    authority_propagated: bool
    client_mutated: bool
    artifact_sha256: str


class SoftwareToAppFactoryHandoff:
    """Bridge validated Software Factory evidence into review-only App Factory intent."""

    def __init__(self, app_factory: AppFactory) -> None:
        self._app_factory = app_factory
        self._artifacts: dict[str, AppFactoryHandoffArtifact] = {}

    def create(self, request: AppFactoryHandoffRequest) -> AppFactoryHandoffArtifact:
        _validate_handoff_id(request.handoff_id)
        if request.handoff_id in self._artifacts:
            raise AppFactoryHandoffError("handoff_id already exists")

        proposal = request.software_proposal
        evidence = proposal.evidence
        execution = request.engineering_execution

        if not proposal.requires_human_approval:
            raise AppFactoryHandoffError(
                "Software Factory proposal must preserve human approval requirement"
            )
        if proposal.production_applied:
            raise AppFactoryHandoffError(
                "production-applied Software Factory output cannot enter SF-9"
            )
        if not evidence.validation.passed:
            raise AppFactoryHandoffError(
                "Software Factory validation must pass before App Factory handoff"
            )
        if _SHA1.fullmatch(evidence.repository_sha) is None:
            raise AppFactoryHandoffError("Software Factory repository SHA is invalid")

        agent_id = execution.admission.agent_id
        verifier_id = execution.verifier_id
        if not agent_id.startswith("ilaios.agent.engineering."):
            raise AppFactoryHandoffError(
                "SF-9 accepts only canonical engineering-agent execution evidence"
            )
        if verifier_id == agent_id:
            raise AppFactoryHandoffError(
                "engineering producer cannot independently verify its own handoff"
            )
        if _SHA256.fullmatch(execution.evidence_digest) is None:
            raise AppFactoryHandoffError("engineering execution evidence digest is invalid")
        if execution.status not in {"READY", "REVIEW_REQUIRED"}:
            raise AppFactoryHandoffError("engineering execution is not handoff-eligible")
        if not execution.skill_results:
            raise AppFactoryHandoffError("engineering execution must contain skill evidence")
        if any(result.status != "READY" for result in execution.skill_results):
            raise AppFactoryHandoffError("all SF-7 skill steps must be READY for handoff")

        goal_sha256 = _goal_digest(request.goal)
        app_request_id = f"sf9-{request.handoff_id}"
        target_path = (
            f"artifacts/app/{request.platform}/handoffs/{request.handoff_id}.json"
        )
        app_request = self._app_factory.propose(
            app_request_id,
            platform=request.platform,
            action=request.action,
            objective=request.goal.objective,
            target_path=target_path,
        )
        _require_review_only_app_request(app_request)

        material = {
            "handoff_id": request.handoff_id,
            "source_capability": SOURCE_CAPABILITY,
            "target_capability": TARGET_CAPABILITY,
            "goal_sha256": goal_sha256,
            "acceptance_criteria": list(request.goal.acceptance_criteria),
            "software_proposal_id": proposal.proposal_id,
            "software_job_id": proposal.job_id,
            "software_evidence_id": evidence.evidence_id,
            "repository_sha": evidence.repository_sha,
            "engineering_agent_id": agent_id,
            "engineering_verifier_id": verifier_id,
            "engineering_execution_sha256": execution.evidence_digest,
            "app_request_id": app_request.request_id,
            "app_request_sha256": app_request.request_sha256,
            "platform": app_request.platform,
            "action": app_request.action,
            "source_review_required": execution.status == "REVIEW_REQUIRED",
            "app_approved_for_review": app_request.approved_for_review,
            "authority_propagated": False,
            "client_mutated": app_request.client_mutated,
        }
        artifact_sha256 = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        artifact = AppFactoryHandoffArtifact(
            handoff_id=request.handoff_id,
            source_capability=SOURCE_CAPABILITY,
            target_capability=TARGET_CAPABILITY,
            goal_sha256=goal_sha256,
            software_proposal_id=proposal.proposal_id,
            software_job_id=proposal.job_id,
            software_evidence_id=evidence.evidence_id,
            repository_sha=evidence.repository_sha,
            engineering_agent_id=agent_id,
            engineering_verifier_id=verifier_id,
            engineering_execution_sha256=execution.evidence_digest,
            app_request_id=app_request.request_id,
            app_request_sha256=app_request.request_sha256,
            platform=app_request.platform,
            action=app_request.action,
            source_review_required=execution.status == "REVIEW_REQUIRED",
            app_approved_for_review=app_request.approved_for_review,
            authority_propagated=False,
            client_mutated=app_request.client_mutated,
            artifact_sha256=artifact_sha256,
        )
        self._artifacts[request.handoff_id] = artifact
        return artifact

    def artifact(self, handoff_id: str) -> AppFactoryHandoffArtifact:
        artifact = self._artifacts.get(handoff_id)
        if artifact is None:
            raise AppFactoryHandoffError("handoff artifact does not exist")
        return artifact


def _validate_handoff_id(handoff_id: str) -> None:
    if _HANDOFF_ID.fullmatch(handoff_id) is None:
        raise AppFactoryHandoffError("handoff_id must be a bounded canonical identifier")


def _require_review_only_app_request(request: AppRequest) -> None:
    if request.approved_for_review or request.approver is not None:
        raise AppFactoryHandoffError("SF-9 cannot propagate App Factory approval")
    if request.client_mutated:
        raise AppFactoryHandoffError("SF-9 cannot propagate client mutation")


def _goal_digest(goal: GoalSpec) -> str:
    material = {
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
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
