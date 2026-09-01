"""SF-11 validation pipeline contract and Software Factory lineage proofs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone

from services.agent_governance import AgentAdmissionEvidence
from services.app_factory import AppFactory
from services.commerce_growth_factory import CommerceGrowthFactory
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    RiskClass,
)
from services.creative_document_factory import CreativeDocumentFactory
from services.integrations.software_app_handoff import (
    AppFactoryHandoffArtifact,
    AppFactoryHandoffRequest,
    SoftwareToAppFactoryHandoff,
)
from services.integrations.software_specialized_handoff import (
    PersonalOperationsPayload,
    SpecializedFactoryHandoffArtifact,
    SpecializedFactoryHandoffRequest,
    SoftwareToSpecializedFactoryHandoff,
)
from services.personal_operations_factory import PersonalOperationsFactory
from services.research_data_factory import ResearchDataFactory
from services.security_factory import SecurityFactory
from services.software_factory import EvidenceBundle, PromotionProposal, ValidationResult
from services.software_factory_agents import EngineeringAgentExecution
from services.software_factory_skills import SkillExecutionResult
from services.software_factory_validation import (
    SoftwareFactoryValidationPipeline,
    SoftwareValidationRequest,
)
from src.core.validation_pipeline import (
    ContractValidationPipeline,
    RuleSeverity,
    ValidationContract,
    ValidationRuleSpec,
    ValidationStatus,
    canonical_sha256,
)

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
REPOSITORY_SHA = "a" * 40
AGENT_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"


def _goal() -> GoalSpec:
    return GoalSpec(
        "Validate a governed Software Factory result.",
        (
            "exact evidence lineage is preserved",
            "no authority propagates through validation",
        ),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal(*, passed: bool = True) -> PromotionProposal:
    validation = ValidationResult(
        passed,
        ("pytest", "ruff", "mypy") if passed else ("pytest",),
        () if passed else ("pytest failed",),
    )
    evidence = EvidenceBundle(
        "evidence-sf11",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        validation,
        "2026-08-14T07:15:00+00:00",
    )
    return PromotionProposal("proposal-sf11", "job-sf11", evidence, True, False)


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf11",
        AGENT_ID,
        VERIFIER_ID,
        NOW,
        True,
        False,
    )
    result = SkillExecutionResult(
        "sf-backend-engineering",
        "1.0.0",
        "READY",
        {"repository_sha": REPOSITORY_SHA},
        None,
        ("repository_base_sha", "reviewer", "validation_results"),
        True,
    )
    status = "REVIEW_REQUIRED"
    digest = canonical_sha256(
        {
            "agent_id": AGENT_ID,
            "invocation_id": admission.invocation_id,
            "verifier_id": VERIFIER_ID,
            "base_sha": REPOSITORY_SHA,
            "status": status,
            "skills": [
                {
                    "skill_id": result.skill_id,
                    "version": result.version,
                    "status": result.status,
                    "evidence": list(result.emitted_evidence),
                    "independent_review_required": True,
                }
            ],
        }
    )
    return EngineeringAgentExecution(admission, (result,), status, digest)


def _validation_request(
    *,
    proposal: PromotionProposal | None = None,
    execution: EngineeringAgentExecution | None = None,
    handoffs: tuple[AppFactoryHandoffArtifact | SpecializedFactoryHandoffArtifact, ...] = (),
    validator_id: str = "ilaios.validator.software-factory.v1",
    environment_id: str = "ci-ephemeral-read-only",
) -> SoftwareValidationRequest:
    return SoftwareValidationRequest(
        pipeline_run_id="sf11-run-1",
        tenant_id="tenant-1",
        task_id="task-1",
        correlation_id="correlation-1",
        validator_id=validator_id,
        environment_id=environment_id,
        policy_reference="policy/software-factory/high-risk/v1",
        goal=_goal(),
        software_proposal=proposal or _proposal(),
        engineering_execution=execution or _execution(),
        handoffs=handoffs,
    )


def _app_handoff(
    proposal: PromotionProposal, execution: EngineeringAgentExecution
) -> AppFactoryHandoffArtifact:
    return SoftwareToAppFactoryHandoff(AppFactory()).create(
        AppFactoryHandoffRequest(
            handoff_id="sf11-app-1",
            goal=_goal(),
            software_proposal=proposal,
            engineering_execution=execution,
            platform="windows",
        )
    )


def _specialized_handoff(
    proposal: PromotionProposal, execution: EngineeringAgentExecution
) -> SpecializedFactoryHandoffArtifact:
    handoff = SoftwareToSpecializedFactoryHandoff(
        ResearchDataFactory(),
        SecurityFactory(),
        CreativeDocumentFactory(),
        CommerceGrowthFactory(),
        PersonalOperationsFactory(),
    )
    return handoff.create(
        SpecializedFactoryHandoffRequest(
            handoff_id="sf11-personal-1",
            goal=_goal(),
            software_proposal=proposal,
            engineering_execution=execution,
            target_capability="ilaios.capability.personal-operations",
            payload=PersonalOperationsPayload(
                "plan-sf11",
                (("step-1", "checklist_draft", "local-review", "Review result"),),
            ),
        )
    )


def _core_contract(
    pipeline: ContractValidationPipeline,
    subject: Mapping[str, object],
    *,
    producer_id: str = "producer",
    validator_id: str = "validator",
    rule_ids: tuple[str, ...] | None = None,
) -> ValidationContract:
    return ValidationContract(
        pipeline_run_id="run-1",
        contract_version="1.0.0",
        tenant_id="tenant-1",
        task_id="task-1",
        correlation_id="correlation-1",
        subject_id="subject-1",
        subject_sha256=canonical_sha256(subject),
        producer_id=producer_id,
        validator_id=validator_id,
        governed_proposal_sha256="e" * 64,
        policy_reference="policy-1",
        rule_set_id="rules-1",
        required_rule_ids=rule_ids or pipeline.rule_ids,
        environment_id="ci-read-only",
        acceptance_criteria=("result is immutable",),
        read_only_environment=True,
    )


def test_contract_pipeline_passes_without_granting_acceptance() -> None:
    pipeline = ContractValidationPipeline(
        (
            ValidationRuleSpec(
                "rule.integrity",
                "1.0.0",
                RuleSeverity.MANDATORY,
                lambda subject: None,
            ),
        )
    )
    subject: dict[str, object] = {"artifact": "exact"}

    report = pipeline.run(_core_contract(pipeline, subject), subject)

    assert report.status is ValidationStatus.PASS
    assert report.passed is True
    assert report.acceptance_authorized is False
    assert report.subject_mutated is False
    assert len(report.report_sha256) == 64


def test_contract_pipeline_blocks_weakened_rule_set_and_self_validation() -> None:
    pipeline = ContractValidationPipeline(
        (
            ValidationRuleSpec(
                "rule.one", "1.0.0", RuleSeverity.MANDATORY, lambda subject: None
            ),
            ValidationRuleSpec(
                "rule.two",
                "1.0.0",
                RuleSeverity.MANDATORY,
                lambda subject: None,
                ("rule.one",),
            ),
        )
    )
    subject: dict[str, object] = {"artifact": "exact"}
    weakened = _core_contract(pipeline, subject, rule_ids=("rule.one",))
    self_validated = _core_contract(
        pipeline, subject, producer_id="same", validator_id="same"
    )

    weakened_report = pipeline.run(weakened, subject)
    self_report = pipeline.run(self_validated, subject)

    assert weakened_report.status is ValidationStatus.BLOCKED
    assert "cannot weaken or reorder" in " ".join(weakened_report.errors)
    assert self_report.status is ValidationStatus.BLOCKED
    assert "cannot validate its own" in " ".join(self_report.errors)


def test_contract_pipeline_blocks_subject_digest_mismatch_and_validator_mutation() -> None:
    def mutating_rule(subject: Mapping[str, object]) -> str | None:
        if isinstance(subject, dict):
            subject["artifact"] = "mutated"
        return None

    pipeline = ContractValidationPipeline(
        (
            ValidationRuleSpec(
                "rule.mutation", "1.0.0", RuleSeverity.MANDATORY, mutating_rule
            ),
        )
    )
    subject: dict[str, object] = {"artifact": "exact"}
    valid_contract = _core_contract(pipeline, subject)
    bad_digest_contract = replace(valid_contract, subject_sha256="f" * 64)

    mismatch = pipeline.run(bad_digest_contract, subject)
    mutated = pipeline.run(valid_contract, subject)

    assert mismatch.status is ValidationStatus.BLOCKED
    assert "digest mismatch" in " ".join(mismatch.errors)
    assert mutated.status is ValidationStatus.BLOCKED
    assert mutated.subject_mutated is True


def test_sf11_validates_software_evidence_and_stops_before_acceptance() -> None:
    pipeline = SoftwareFactoryValidationPipeline()

    report = pipeline.validate(_validation_request())

    assert report.status is ValidationStatus.PASS
    assert report.acceptance_authorized is False
    assert report.subject_mutated is False
    assert tuple(result.rule_id for result in report.rule_results) == pipeline.rule_ids
    assert len(report.report_sha256) == 64


def test_sf11_validates_app_and_specialized_handoff_lineage() -> None:
    proposal = _proposal()
    execution = _execution()
    app = _app_handoff(proposal, execution)
    specialized = _specialized_handoff(proposal, execution)

    report = SoftwareFactoryValidationPipeline().validate(
        _validation_request(
            proposal=proposal,
            execution=execution,
            handoffs=(app, specialized),
        )
    )

    assert report.status is ValidationStatus.PASS
    assert report.acceptance_authorized is False


def test_sf11_fails_tampered_engineering_execution_digest() -> None:
    execution = replace(_execution(), evidence_digest="f" * 64)

    report = SoftwareFactoryValidationPipeline().validate(
        _validation_request(execution=execution)
    )

    assert report.status is ValidationStatus.FAIL
    assert "engineering execution evidence digest mismatch" in " ".join(report.errors)


def test_sf11_rejects_failed_source_validation() -> None:
    report = SoftwareFactoryValidationPipeline().validate(
        _validation_request(proposal=_proposal(passed=False))
    )

    assert report.status is ValidationStatus.FAIL
    assert "validation evidence did not pass" in " ".join(report.errors)


def test_sf11_rejects_forbidden_authority_even_if_handoff_hash_is_consistent() -> None:
    proposal = _proposal()
    execution = _execution()
    app = _app_handoff(proposal, execution)
    material = {
        "handoff_id": app.handoff_id,
        "source_capability": app.source_capability,
        "target_capability": app.target_capability,
        "goal_sha256": app.goal_sha256,
        "acceptance_criteria": list(_goal().acceptance_criteria),
        "software_proposal_id": app.software_proposal_id,
        "software_job_id": app.software_job_id,
        "software_evidence_id": app.software_evidence_id,
        "repository_sha": app.repository_sha,
        "engineering_agent_id": app.engineering_agent_id,
        "engineering_verifier_id": app.engineering_verifier_id,
        "engineering_execution_sha256": app.engineering_execution_sha256,
        "app_request_id": app.app_request_id,
        "app_request_sha256": app.app_request_sha256,
        "platform": app.platform,
        "action": app.action,
        "source_review_required": app.source_review_required,
        "app_approved_for_review": app.app_approved_for_review,
        "authority_propagated": True,
        "client_mutated": app.client_mutated,
    }
    malicious = replace(
        app,
        authority_propagated=True,
        artifact_sha256=canonical_sha256(material),
    )

    report = SoftwareFactoryValidationPipeline().validate(
        _validation_request(
            proposal=proposal,
            execution=execution,
            handoffs=(malicious,),
        )
    )

    assert report.status is ValidationStatus.FAIL
    assert "authority propagation is forbidden" in " ".join(report.errors)


def test_sf11_fails_blocked_specialized_target_even_with_consistent_hash() -> None:
    proposal = _proposal()
    execution = _execution()
    artifact = _specialized_handoff(proposal, execution)
    material = {
        "handoff_id": artifact.handoff_id,
        "source_capability": artifact.source_capability,
        "target_capability": artifact.target_capability,
        "goal_sha256": artifact.goal_sha256,
        "acceptance_criteria": list(_goal().acceptance_criteria),
        "software_proposal_id": artifact.software_proposal_id,
        "software_job_id": artifact.software_job_id,
        "software_evidence_id": artifact.software_evidence_id,
        "repository_sha": artifact.repository_sha,
        "engineering_agent_id": artifact.engineering_agent_id,
        "engineering_verifier_id": artifact.engineering_verifier_id,
        "engineering_execution_sha256": artifact.engineering_execution_sha256,
        "target_object_id": artifact.target_object_id,
        "target_output_sha256": artifact.target_output_sha256,
        "target_status": "BLOCKED",
        "target_approved": artifact.target_approved,
        "independent_verification_completed": artifact.independent_verification_completed,
        "authority_propagated": artifact.authority_propagated,
        "external_applied": artifact.external_applied,
    }
    blocked = replace(
        artifact,
        target_status="BLOCKED",
        artifact_sha256=canonical_sha256(material),
    )

    report = SoftwareFactoryValidationPipeline().validate(
        _validation_request(
            proposal=proposal,
            execution=execution,
            handoffs=(blocked,),
        )
    )

    assert report.status is ValidationStatus.FAIL
    assert "specialized factory target is blocked" in " ".join(report.errors)


def test_sf11_rejects_unapproved_environment_and_self_validator() -> None:
    pipeline = SoftwareFactoryValidationPipeline()
    wrong_environment = pipeline.validate(
        _validation_request(environment_id="production-mutable")
    )
    self_validator = pipeline.validate(_validation_request(validator_id=AGENT_ID))

    assert wrong_environment.status is ValidationStatus.FAIL
    assert "approved read-only environment" in " ".join(wrong_environment.errors)
    assert self_validator.status is ValidationStatus.BLOCKED
    assert "cannot validate its own" in " ".join(self_validator.errors)
