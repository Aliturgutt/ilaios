"""SF-11 validation pipeline over canonical Software Factory evidence.

The adapter reuses the core ContractValidationPipeline and validates the exact
SF-7 through SF-10 evidence chain without granting acceptance, approval,
promotion, deployment, repair, or mutation authority. SF-12 independent review
remains a separate phase.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias, cast

from services.control_plane.proposals import GoalSpec
from services.integrations.software_app_handoff import AppFactoryHandoffArtifact
from services.integrations.software_specialized_handoff import (
    SOURCE_CAPABILITY,
    SPECIALIZED_TARGETS,
    SpecializedFactoryHandoffArtifact,
)
from services.software_factory import PromotionProposal
from services.software_factory_agents import EngineeringAgentExecution
from src.core.validation_pipeline import (
    ContractValidationPipeline,
    RuleSeverity,
    ValidationContract,
    ValidationReport,
    ValidationRuleSpec,
    canonical_sha256,
)

RULE_SET_ID = "ilaios.validation.software-factory.v1"
CONTRACT_VERSION = "1.0.0"
APP_FACTORY_CAPABILITY = "ilaios.capability.app-factory"
ALLOWED_VALIDATION_ENVIRONMENTS = frozenset(
    {"ci-ephemeral-read-only", "local-deterministic-read-only"}
)
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

CrossFactoryArtifact: TypeAlias = (
    AppFactoryHandoffArtifact | SpecializedFactoryHandoffArtifact
)


@dataclass(frozen=True, slots=True)
class SoftwareValidationRequest:
    """Exact SF-11 validation request with no delivery or acceptance authority."""

    pipeline_run_id: str
    tenant_id: str
    task_id: str
    correlation_id: str
    validator_id: str
    environment_id: str
    policy_reference: str
    goal: GoalSpec
    software_proposal: PromotionProposal
    engineering_execution: EngineeringAgentExecution
    handoffs: tuple[CrossFactoryArtifact, ...] = ()


class SoftwareFactoryValidationPipeline:
    """Validate canonical Software Factory lineage through fixed SF-11 rules."""

    def __init__(self) -> None:
        self._pipeline = ContractValidationPipeline(
            (
                ValidationRuleSpec(
                    "sf11.proposal-evidence",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_proposal_evidence,
                ),
                ValidationRuleSpec(
                    "sf11.engineering-evidence",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_engineering_evidence,
                    ("sf11.proposal-evidence",),
                ),
                ValidationRuleSpec(
                    "sf11.cross-factory-lineage",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_cross_factory_lineage,
                    ("sf11.engineering-evidence",),
                ),
                ValidationRuleSpec(
                    "sf11.authority-boundary",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_authority_boundary,
                    ("sf11.cross-factory-lineage",),
                ),
                ValidationRuleSpec(
                    "sf11.environment-boundary",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_environment,
                    ("sf11.authority-boundary",),
                ),
                ValidationRuleSpec(
                    "sf11.acceptance-readiness",
                    "1.0.0",
                    RuleSeverity.MANDATORY,
                    _validate_acceptance_readiness,
                    ("sf11.environment-boundary",),
                ),
            )
        )

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return self._pipeline.rule_ids

    def validate(self, request: SoftwareValidationRequest) -> ValidationReport:
        subject = _subject_material(request)
        proposal_material = _proposal_material(request.software_proposal)
        contract = ValidationContract(
            pipeline_run_id=request.pipeline_run_id,
            contract_version=CONTRACT_VERSION,
            tenant_id=request.tenant_id,
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            subject_id=f"software-factory:{request.software_proposal.proposal_id}",
            subject_sha256=canonical_sha256(subject),
            producer_id=request.engineering_execution.admission.agent_id,
            validator_id=request.validator_id,
            governed_proposal_sha256=canonical_sha256(proposal_material),
            policy_reference=request.policy_reference,
            rule_set_id=RULE_SET_ID,
            required_rule_ids=self._pipeline.rule_ids,
            environment_id=request.environment_id,
            acceptance_criteria=request.goal.acceptance_criteria,
            read_only_environment=True,
        )
        return self._pipeline.run(contract, subject)


def _subject_material(request: SoftwareValidationRequest) -> dict[str, object]:
    return {
        "goal": _goal_material(request.goal),
        "proposal": _proposal_material(request.software_proposal),
        "engineering": _engineering_material(request.engineering_execution),
        "handoffs": [
            _handoff_material(handoff) for handoff in request.handoffs
        ],
        "environment_id": request.environment_id,
        "policy_reference": request.policy_reference,
    }


def _goal_material(goal: GoalSpec) -> dict[str, object]:
    material: dict[str, object] = {
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
    material["sha256"] = canonical_sha256(material)
    return material


def _proposal_material(proposal: PromotionProposal) -> dict[str, object]:
    evidence = proposal.evidence
    return {
        "proposal_id": proposal.proposal_id,
        "job_id": proposal.job_id,
        "requires_human_approval": proposal.requires_human_approval,
        "production_applied": proposal.production_applied,
        "evidence_id": evidence.evidence_id,
        "repository_sha": evidence.repository_sha,
        "changeset_sha256": evidence.changeset_sha256,
        "workspace_sha256": evidence.workspace_sha256,
        "validation_passed": evidence.validation.passed,
        "validation_checks": list(evidence.validation.checks),
        "validation_errors": list(evidence.validation.errors),
        "created_at": evidence.created_at,
    }


def _engineering_material(execution: EngineeringAgentExecution) -> dict[str, object]:
    return {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "security_scan_passed": execution.admission.security_scan_passed,
        "dlp_approved": execution.admission.dlp_approved,
        "status": execution.status,
        "evidence_digest": execution.evidence_digest,
        "skills": [
            {
                "skill_id": result.skill_id,
                "version": result.version,
                "status": result.status,
                "emitted_evidence": list(result.emitted_evidence),
                "independent_review_required": result.independent_review_required,
            }
            for result in execution.skill_results
        ],
    }


def _handoff_material(handoff: CrossFactoryArtifact) -> dict[str, object]:
    if isinstance(handoff, AppFactoryHandoffArtifact):
        return {
            "kind": "app",
            "handoff_id": handoff.handoff_id,
            "source_capability": handoff.source_capability,
            "target_capability": handoff.target_capability,
            "goal_sha256": handoff.goal_sha256,
            "software_proposal_id": handoff.software_proposal_id,
            "software_job_id": handoff.software_job_id,
            "software_evidence_id": handoff.software_evidence_id,
            "repository_sha": handoff.repository_sha,
            "engineering_agent_id": handoff.engineering_agent_id,
            "engineering_verifier_id": handoff.engineering_verifier_id,
            "engineering_execution_sha256": handoff.engineering_execution_sha256,
            "app_request_id": handoff.app_request_id,
            "app_request_sha256": handoff.app_request_sha256,
            "platform": handoff.platform,
            "action": handoff.action,
            "source_review_required": handoff.source_review_required,
            "app_approved_for_review": handoff.app_approved_for_review,
            "authority_propagated": handoff.authority_propagated,
            "client_mutated": handoff.client_mutated,
            "artifact_sha256": handoff.artifact_sha256,
        }
    return {
        "kind": "specialized",
        "handoff_id": handoff.handoff_id,
        "source_capability": handoff.source_capability,
        "target_capability": handoff.target_capability,
        "goal_sha256": handoff.goal_sha256,
        "software_proposal_id": handoff.software_proposal_id,
        "software_job_id": handoff.software_job_id,
        "software_evidence_id": handoff.software_evidence_id,
        "repository_sha": handoff.repository_sha,
        "engineering_agent_id": handoff.engineering_agent_id,
        "engineering_verifier_id": handoff.engineering_verifier_id,
        "engineering_execution_sha256": handoff.engineering_execution_sha256,
        "target_object_id": handoff.target_object_id,
        "target_output_sha256": handoff.target_output_sha256,
        "target_status": handoff.target_status,
        "target_approved": handoff.target_approved,
        "independent_verification_completed": handoff.independent_verification_completed,
        "authority_propagated": handoff.authority_propagated,
        "external_applied": handoff.external_applied,
        "artifact_sha256": handoff.artifact_sha256,
    }


def _validate_proposal_evidence(subject: Mapping[str, object]) -> str | None:
    proposal = _mapping(subject.get("proposal"), "proposal")
    if proposal.get("requires_human_approval") is not True:
        return "Software Factory human-approval requirement is missing"
    if proposal.get("production_applied") is not False:
        return "production-applied output is not validation eligible"
    if proposal.get("validation_passed") is not True:
        return "Software Factory validation evidence did not pass"
    checks = _object_list(proposal.get("validation_checks"), "validation_checks")
    errors = _object_list(proposal.get("validation_errors"), "validation_errors")
    if not checks:
        return "Software Factory validation evidence has no executed checks"
    if errors:
        return "Software Factory validation evidence contains errors"
    if _SHA1.fullmatch(_text(proposal.get("repository_sha"), "repository_sha")) is None:
        return "repository SHA is invalid"
    for field in ("changeset_sha256", "workspace_sha256"):
        if _SHA256.fullmatch(_text(proposal.get(field), field)) is None:
            return f"{field} is invalid"
    for field in ("proposal_id", "job_id", "evidence_id", "created_at"):
        if not _trimmed(_text(proposal.get(field), field)):
            return f"{field} must be non-blank and trimmed"
    return None


def _validate_engineering_evidence(subject: Mapping[str, object]) -> str | None:
    proposal = _mapping(subject.get("proposal"), "proposal")
    engineering = _mapping(subject.get("engineering"), "engineering")
    agent_id = _text(engineering.get("agent_id"), "agent_id")
    verifier_id = _text(engineering.get("verifier_id"), "verifier_id")
    if not agent_id.startswith("ilaios.agent.engineering."):
        return "validation subject was not produced by a canonical engineering agent"
    if agent_id == verifier_id:
        return "engineering producer cannot be its own verifier"
    if engineering.get("security_scan_passed") is not True:
        return "engineering admission lacks required security scan evidence"
    status = _text(engineering.get("status"), "engineering status")
    if status not in {"READY", "REVIEW_REQUIRED"}:
        return "engineering execution state is not validation eligible"
    skills = _object_list(engineering.get("skills"), "skills")
    if not skills:
        return "engineering execution contains no SF-7 skill evidence"
    normalized_skills: list[dict[str, object]] = []
    skill_ids: list[str] = []
    for raw in skills:
        skill = _mapping(raw, "skill")
        skill_id = _text(skill.get("skill_id"), "skill_id")
        version = _text(skill.get("version"), "skill version")
        if not _trimmed(skill_id) or not _trimmed(version):
            return "SF-7 skill identity/version is invalid"
        if skill.get("status") != "READY":
            return "all SF-7 skill results must be READY"
        emitted = _object_list(skill.get("emitted_evidence"), "emitted_evidence")
        if not emitted or not all(isinstance(item, str) and item.strip() for item in emitted):
            return "SF-7 skill result is missing evidence classes"
        skill_ids.append(skill_id)
        normalized_skills.append(
            {
                "skill_id": skill_id,
                "version": version,
                "status": "READY",
                "evidence": emitted,
                "independent_review_required": skill.get(
                    "independent_review_required"
                )
                is True,
            }
        )
    if len(skill_ids) != len(set(skill_ids)):
        return "SF-7 validation subject contains duplicate skill results"

    base_sha = _text(proposal.get("repository_sha"), "repository_sha")
    expected = canonical_sha256(
        {
            "agent_id": agent_id,
            "invocation_id": _text(
                engineering.get("invocation_id"), "invocation_id"
            ),
            "verifier_id": verifier_id,
            "base_sha": base_sha,
            "status": status,
            "skills": normalized_skills,
        }
    )
    actual = _text(engineering.get("evidence_digest"), "evidence_digest")
    if _SHA256.fullmatch(actual) is None or actual != expected:
        return "engineering execution evidence digest mismatch"
    return None


def _validate_cross_factory_lineage(subject: Mapping[str, object]) -> str | None:
    proposal = _mapping(subject.get("proposal"), "proposal")
    engineering = _mapping(subject.get("engineering"), "engineering")
    goal = _mapping(subject.get("goal"), "goal")
    handoffs = _object_list(subject.get("handoffs"), "handoffs")
    seen_ids: set[str] = set()
    for raw in handoffs:
        handoff = _mapping(raw, "handoff")
        handoff_id = _text(handoff.get("handoff_id"), "handoff_id")
        if handoff_id in seen_ids:
            return "cross-factory handoff IDs must be unique"
        seen_ids.add(handoff_id)
        common_error = _validate_common_handoff(
            handoff, proposal=proposal, engineering=engineering, goal=goal
        )
        if common_error is not None:
            return common_error
        kind = handoff.get("kind")
        if kind == "app":
            error = _validate_app_handoff_digest(handoff, goal)
        elif kind == "specialized":
            error = _validate_specialized_handoff_digest(handoff, goal)
        else:
            return "unknown cross-factory handoff kind"
        if error is not None:
            return error
    return None


def _validate_common_handoff(
    handoff: Mapping[str, object],
    *,
    proposal: Mapping[str, object],
    engineering: Mapping[str, object],
    goal: Mapping[str, object],
) -> str | None:
    expected_pairs = (
        ("source_capability", SOURCE_CAPABILITY),
        ("software_proposal_id", proposal.get("proposal_id")),
        ("software_job_id", proposal.get("job_id")),
        ("software_evidence_id", proposal.get("evidence_id")),
        ("repository_sha", proposal.get("repository_sha")),
        ("engineering_agent_id", engineering.get("agent_id")),
        ("engineering_verifier_id", engineering.get("verifier_id")),
        ("engineering_execution_sha256", engineering.get("evidence_digest")),
        ("goal_sha256", goal.get("sha256")),
    )
    for field, expected in expected_pairs:
        if handoff.get(field) != expected:
            return f"cross-factory lineage mismatch: {field}"
    return None


def _validate_app_handoff_digest(
    handoff: Mapping[str, object], goal: Mapping[str, object]
) -> str | None:
    if handoff.get("target_capability") != APP_FACTORY_CAPABILITY:
        return "app handoff target capability is invalid"
    if handoff.get("source_review_required") not in {True, False}:
        return "app handoff source review state is invalid"
    material = {
        "handoff_id": handoff.get("handoff_id"),
        "source_capability": handoff.get("source_capability"),
        "target_capability": handoff.get("target_capability"),
        "goal_sha256": handoff.get("goal_sha256"),
        "acceptance_criteria": goal.get("acceptance_criteria"),
        "software_proposal_id": handoff.get("software_proposal_id"),
        "software_job_id": handoff.get("software_job_id"),
        "software_evidence_id": handoff.get("software_evidence_id"),
        "repository_sha": handoff.get("repository_sha"),
        "engineering_agent_id": handoff.get("engineering_agent_id"),
        "engineering_verifier_id": handoff.get("engineering_verifier_id"),
        "engineering_execution_sha256": handoff.get(
            "engineering_execution_sha256"
        ),
        "app_request_id": handoff.get("app_request_id"),
        "app_request_sha256": handoff.get("app_request_sha256"),
        "platform": handoff.get("platform"),
        "action": handoff.get("action"),
        "source_review_required": handoff.get("source_review_required"),
        "app_approved_for_review": handoff.get("app_approved_for_review"),
        "authority_propagated": handoff.get("authority_propagated"),
        "client_mutated": handoff.get("client_mutated"),
    }
    actual = _text(handoff.get("artifact_sha256"), "artifact_sha256")
    if _SHA256.fullmatch(actual) is None or canonical_sha256(material) != actual:
        return "App Factory handoff artifact digest mismatch"
    return None


def _validate_specialized_handoff_digest(
    handoff: Mapping[str, object], goal: Mapping[str, object]
) -> str | None:
    target = _text(handoff.get("target_capability"), "target_capability")
    if target not in SPECIALIZED_TARGETS:
        return "specialized handoff target capability is invalid"
    status = handoff.get("target_status")
    if status not in {"REVIEW_REQUIRED", "BLOCKED"}:
        return "specialized handoff target state is invalid"
    material = {
        "handoff_id": handoff.get("handoff_id"),
        "source_capability": handoff.get("source_capability"),
        "target_capability": target,
        "goal_sha256": handoff.get("goal_sha256"),
        "acceptance_criteria": goal.get("acceptance_criteria"),
        "software_proposal_id": handoff.get("software_proposal_id"),
        "software_job_id": handoff.get("software_job_id"),
        "software_evidence_id": handoff.get("software_evidence_id"),
        "repository_sha": handoff.get("repository_sha"),
        "engineering_agent_id": handoff.get("engineering_agent_id"),
        "engineering_verifier_id": handoff.get("engineering_verifier_id"),
        "engineering_execution_sha256": handoff.get(
            "engineering_execution_sha256"
        ),
        "target_object_id": handoff.get("target_object_id"),
        "target_output_sha256": handoff.get("target_output_sha256"),
        "target_status": status,
        "target_approved": handoff.get("target_approved"),
        "independent_verification_completed": handoff.get(
            "independent_verification_completed"
        ),
        "authority_propagated": handoff.get("authority_propagated"),
        "external_applied": handoff.get("external_applied"),
    }
    actual = _text(handoff.get("artifact_sha256"), "artifact_sha256")
    if _SHA256.fullmatch(actual) is None or canonical_sha256(material) != actual:
        return "specialized factory handoff artifact digest mismatch"
    if status == "BLOCKED":
        return "specialized factory target is blocked"
    return None


def _validate_authority_boundary(subject: Mapping[str, object]) -> str | None:
    proposal = _mapping(subject.get("proposal"), "proposal")
    if proposal.get("production_applied") is not False:
        return "validation cannot inherit production authority"
    for raw in _object_list(subject.get("handoffs"), "handoffs"):
        handoff = _mapping(raw, "handoff")
        if handoff.get("authority_propagated") is not False:
            return "cross-factory authority propagation is forbidden"
        if handoff.get("kind") == "app":
            if handoff.get("app_approved_for_review") is not False:
                return "SF-11 cannot inherit App Factory approval"
            if handoff.get("client_mutated") is not False:
                return "SF-11 cannot validate a client mutation as review-only"
        else:
            if handoff.get("target_approved") is not False:
                return "SF-11 cannot inherit specialized-factory approval"
            if handoff.get("independent_verification_completed") is not False:
                return "SF-12 independent review cannot be pre-completed by SF-11"
            if handoff.get("external_applied") is not False:
                return "SF-11 cannot validate externally applied specialized output"
    return None


def _validate_environment(subject: Mapping[str, object]) -> str | None:
    environment = _text(subject.get("environment_id"), "environment_id")
    if environment not in ALLOWED_VALIDATION_ENVIRONMENTS:
        return "validation environment is not an approved read-only environment"
    if not _trimmed(_text(subject.get("policy_reference"), "policy_reference")):
        return "validation requires a governed policy reference"
    return None


def _validate_acceptance_readiness(subject: Mapping[str, object]) -> str | None:
    goal = _mapping(subject.get("goal"), "goal")
    criteria = _object_list(goal.get("acceptance_criteria"), "acceptance_criteria")
    if not criteria or not all(isinstance(item, str) and item.strip() for item in criteria):
        return "explicit acceptance criteria are required"
    digest_material = {
        "objective": goal.get("objective"),
        "acceptance_criteria": criteria,
        "risk_class": goal.get("risk_class"),
        "data_class": goal.get("data_class"),
        "budget": goal.get("budget"),
    }
    if canonical_sha256(digest_material) != goal.get("sha256"):
        return "GoalSpec digest mismatch"
    return None


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    return cast(Mapping[str, object], value)


def _object_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    return value


def _trimmed(value: str) -> bool:
    return bool(value) and value == value.strip()
