"""SF-12 independent-review evidence and separation-of-duties tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentAdmissionEvidence
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    RiskClass,
)
from services.software_factory import (
    EvidenceBundle,
    PromotionProposal,
    SoftwareFactoryError,
    ValidationResult,
)
from services.software_factory_agents import EngineeringAgentExecution
from services.software_factory_review import (
    IndependentReviewSubmission,
    ReviewDecision,
    ReviewFinding,
    SoftwareFactoryIndependentReview,
    SoftwareIndependentReviewRequest,
)
from services.software_factory_skills import (
    SkillExecutionResult,
    SkillRegistry,
    default_skills_root,
)
from services.software_factory_validation import (
    SoftwareFactoryValidationPipeline,
    SoftwareValidationRequest,
)
from src.core.validation_pipeline import canonical_sha256

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
REPOSITORY_SHA = "a" * 40
AGENT_ID = "ilaios.agent.engineering.backend.v1"
VERIFIER_ID = "ilaios.agent.meta.independent-verifier.v1"
VALIDATOR_ID = "ilaios.validator.software-factory.v1"
CODE_REVIEWER = "ilaios.reviewer.code.independent.v1"
SECURITY_REVIEWER = "ilaios.reviewer.security.independent.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGED_PATHS = ("services/example.py", "tests/test_example.py")


def _goal() -> GoalSpec:
    return GoalSpec(
        "Review a governed Software Factory result.",
        (
            "exact evidence lineage is preserved",
            "independent review cannot self-certify generated work",
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
        "evidence-sf12",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        validation,
        "2026-08-14T08:15:00+00:00",
    )
    return PromotionProposal("proposal-sf12", "job-sf12", evidence, True, False)


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf12",
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


def _validation_request(*, proposal: PromotionProposal | None = None) -> SoftwareValidationRequest:
    return SoftwareValidationRequest(
        pipeline_run_id="sf11-run-for-sf12",
        tenant_id="tenant-1",
        task_id="task-1",
        correlation_id="correlation-1",
        validator_id=VALIDATOR_ID,
        environment_id="ci-ephemeral-read-only",
        policy_reference="policy/software-factory/high-risk/v1",
        goal=_goal(),
        software_proposal=proposal or _proposal(),
        engineering_execution=_execution(),
    )


def _finding(finding_id: str = "finding-1") -> ReviewFinding:
    return ReviewFinding(
        finding_id,
        "HIGH",
        "services/example.py:example_symbol",
        "evidence://sf12/example",
        "The proposed behavior requires remediation.",
        "Apply a bounded fix and re-run validation.",
        "OPEN",
    )


def _submission(
    skill_id: str,
    report_sha256: str,
    subject_sha256: str,
    *,
    reviewer_id: str | None = None,
    decision: ReviewDecision = ReviewDecision.APPROVE,
    findings: tuple[ReviewFinding, ...] = (),
    reviewed_paths: tuple[str, ...] = CHANGED_PATHS,
) -> IndependentReviewSubmission:
    default_reviewer = CODE_REVIEWER if skill_id == "sf-code-review" else SECURITY_REVIEWER
    return IndependentReviewSubmission(
        skill_id=skill_id,
        skill_version="1.0.0",
        reviewer_id=reviewer_id or default_reviewer,
        reviewed_subject_sha256=subject_sha256,
        validation_report_sha256=report_sha256,
        reviewed_paths=reviewed_paths,
        findings=findings,
        decision=decision,
        evidence_references=(f"evidence://sf12/{skill_id}",),
        read_only=True,
    )


def _request(
    *,
    validation_request: SoftwareValidationRequest | None = None,
    submissions: tuple[IndependentReviewSubmission, ...] | None = None,
) -> SoftwareIndependentReviewRequest:
    sf11_request = validation_request or _validation_request()
    report = SoftwareFactoryValidationPipeline().validate(sf11_request)
    resolved_submissions = submissions or (
        _submission("sf-code-review", report.report_sha256, report.subject_sha256),
        _submission("sf-security-review", report.report_sha256, report.subject_sha256),
    )
    return SoftwareIndependentReviewRequest(
        review_id="sf12-review-1",
        tenant_id=sf11_request.tenant_id,
        task_id=sf11_request.task_id,
        correlation_id=sf11_request.correlation_id,
        policy_reference=sf11_request.policy_reference,
        environment_id=sf11_request.environment_id,
        changed_paths=CHANGED_PATHS,
        validation_request=sf11_request,
        validation_report=report,
        submissions=resolved_submissions,
    )


def _reviewer() -> SoftwareFactoryIndependentReview:
    return SoftwareFactoryIndependentReview(
        SkillRegistry(default_skills_root(REPO_ROOT))
    )


def test_independent_review_approves_without_granting_downstream_authority() -> None:
    record = _reviewer().review(_request())

    assert record.decision is ReviewDecision.APPROVE
    assert record.approved is True
    assert record.review_complete is True
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False
    assert record.production_applied is False
    assert tuple(submission.skill_id for submission in record.submissions) == (
        "sf-code-review",
        "sf-security-review",
    )
    assert record.reviewers == tuple(sorted((CODE_REVIEWER, SECURITY_REVIEWER)))
    assert len(record.record_sha256) == 64


def test_reviewers_must_be_independent_from_producer_verifier_and_validator() -> None:
    base = _request()
    blocked_reviewers = (AGENT_ID, VERIFIER_ID, VALIDATOR_ID)
    for reviewer_id in blocked_reviewers:
        code = replace(base.submissions[0], reviewer_id=reviewer_id)
        request = replace(base, submissions=(code, base.submissions[1]))
        with pytest.raises(SoftwareFactoryError, match="must be independent"):
            _reviewer().review(request)


def test_review_rejects_stale_or_tampered_sf11_report() -> None:
    request = _request()
    tampered = replace(request.validation_report, report_sha256="f" * 64)

    with pytest.raises(SoftwareFactoryError, match="stale or tampered"):
        _reviewer().review(replace(request, validation_report=tampered))


def test_review_requires_exact_code_and_security_review_skill_set() -> None:
    request = _request()

    with pytest.raises(SoftwareFactoryError, match="requires code and security"):
        _reviewer().review(replace(request, submissions=(request.submissions[0],)))

    duplicate = (request.submissions[0], request.submissions[0])
    with pytest.raises(SoftwareFactoryError, match="incomplete or duplicated"):
        _reviewer().review(replace(request, submissions=duplicate))


def test_review_requires_exact_changed_path_scope() -> None:
    request = _request()
    code = replace(request.submissions[0], reviewed_paths=("services/other.py",))

    with pytest.raises(SoftwareFactoryError, match="exact changed-path scope"):
        _reviewer().review(replace(request, submissions=(code, request.submissions[1])))


def test_nonapproval_decision_requires_evidence_backed_finding() -> None:
    request = _request()
    code = replace(
        request.submissions[0],
        decision=ReviewDecision.CHANGES_REQUIRED,
        findings=(),
    )

    with pytest.raises(SoftwareFactoryError, match="requires a finding"):
        _reviewer().review(replace(request, submissions=(code, request.submissions[1])))


def test_review_aggregate_uses_fail_closed_decision_precedence() -> None:
    request = _request()
    code = replace(
        request.submissions[0],
        decision=ReviewDecision.CHANGES_REQUIRED,
        findings=(_finding("code-1"),),
    )
    security = replace(
        request.submissions[1],
        decision=ReviewDecision.REJECT,
        findings=(_finding("security-1"),),
    )

    record = _reviewer().review(replace(request, submissions=(code, security)))

    assert record.decision is ReviewDecision.REJECT
    assert record.approved is False
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False


def test_review_finding_contract_requires_all_canonical_fields() -> None:
    request = _request()
    invalid = replace(_finding(), reason="")
    code = replace(
        request.submissions[0],
        decision=ReviewDecision.CHANGES_REQUIRED,
        findings=(invalid,),
    )

    with pytest.raises(SoftwareFactoryError, match="finding fields"):
        _reviewer().review(replace(request, submissions=(code, request.submissions[1])))


def test_review_cannot_consume_failed_sf11_validation() -> None:
    sf11_request = _validation_request(proposal=_proposal(passed=False))
    request = _request(validation_request=sf11_request)

    with pytest.raises(SoftwareFactoryError, match="passing SF-11"):
        _reviewer().review(request)


def test_canonical_review_skills_remain_bound_to_independent_verification() -> None:
    registry = SkillRegistry(default_skills_root(REPO_ROOT))
    for skill_id in ("sf-code-review", "sf-security-review"):
        manifest = registry.resolve(skill_id).manifest
        assert manifest.domain == "independent-verification"
        assert manifest.independent_review_required is True
        assert "reviewer" in manifest.emitted_evidence
        assert "validation_results" in manifest.emitted_evidence
