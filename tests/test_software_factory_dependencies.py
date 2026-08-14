"""SF-13 dependency-governance policy, lineage, and authority-boundary tests."""

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
from services.software_factory_dependencies import (
    CommercialCompatibility,
    DependencyChange,
    DependencyDisposition,
    DependencyGovernanceRequest,
    DependencyOperation,
    DependencyPolicy,
    DependencyRole,
    DependencySecurityStatus,
    SoftwareFactoryDependencyGovernance,
)
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
CHANGED_PATHS = ("pyproject.toml", "uv.lock", "services/example.py")


def _registry() -> SkillRegistry:
    return SkillRegistry(default_skills_root(REPO_ROOT))


def _goal() -> GoalSpec:
    return GoalSpec(
        "Govern a reviewed dependency change.",
        (
            "dependency provenance is explicit",
            "commercial and security policy is enforced",
        ),
        RiskClass.HIGH,
        DataClass.INTERNAL,
        BudgetEnvelope(3, 600),
    )


def _proposal() -> PromotionProposal:
    evidence = EvidenceBundle(
        "evidence-sf13",
        REPOSITORY_SHA,
        "b" * 64,
        "c" * 64,
        ValidationResult(True, ("pytest", "ruff", "mypy"), ()),
        "2026-08-14T09:00:00+00:00",
    )
    return PromotionProposal("proposal-sf13", "job-sf13", evidence, True, False)


def _execution() -> EngineeringAgentExecution:
    admission = AgentAdmissionEvidence(
        "invoke-sf13",
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


def _validation_request() -> SoftwareValidationRequest:
    return SoftwareValidationRequest(
        pipeline_run_id="sf11-run-for-sf13",
        tenant_id="tenant-1",
        task_id="task-1",
        correlation_id="correlation-1",
        validator_id=VALIDATOR_ID,
        environment_id="ci-ephemeral-read-only",
        policy_reference="policy/software-factory/critical-risk/v1",
        goal=_goal(),
        software_proposal=_proposal(),
        engineering_execution=_execution(),
    )


def _submission(
    skill_id: str,
    report_sha256: str,
    subject_sha256: str,
    *,
    decision: ReviewDecision = ReviewDecision.APPROVE,
    findings: tuple[ReviewFinding, ...] = (),
) -> IndependentReviewSubmission:
    reviewer_id = CODE_REVIEWER if skill_id == "sf-code-review" else SECURITY_REVIEWER
    return IndependentReviewSubmission(
        skill_id=skill_id,
        skill_version="1.0.0",
        reviewer_id=reviewer_id,
        reviewed_subject_sha256=subject_sha256,
        validation_report_sha256=report_sha256,
        reviewed_paths=CHANGED_PATHS,
        findings=findings,
        decision=decision,
        evidence_references=(f"evidence://sf13/{skill_id}",),
        read_only=True,
    )


def _review_bundle(
    *, nonapproved: bool = False
) -> tuple[SoftwareIndependentReviewRequest, object]:
    validation_request = _validation_request()
    report = SoftwareFactoryValidationPipeline().validate(validation_request)
    code_findings: tuple[ReviewFinding, ...] = ()
    code_decision = ReviewDecision.APPROVE
    if nonapproved:
        code_decision = ReviewDecision.CHANGES_REQUIRED
        code_findings = (
            ReviewFinding(
                "dep-review-1",
                "HIGH",
                "pyproject.toml:dependencies",
                "evidence://sf13/dependency-review",
                "Dependency evidence needs remediation.",
                "Repair evidence and repeat review.",
                "OPEN",
            ),
        )
    request = SoftwareIndependentReviewRequest(
        review_id="sf12-review-for-sf13",
        tenant_id=validation_request.tenant_id,
        task_id=validation_request.task_id,
        correlation_id=validation_request.correlation_id,
        policy_reference=validation_request.policy_reference,
        environment_id=validation_request.environment_id,
        changed_paths=CHANGED_PATHS,
        validation_request=validation_request,
        validation_report=report,
        submissions=(
            _submission(
                "sf-code-review",
                report.report_sha256,
                report.subject_sha256,
                decision=code_decision,
                findings=code_findings,
            ),
            _submission("sf-security-review", report.report_sha256, report.subject_sha256),
        ),
    )
    record = SoftwareFactoryIndependentReview(_registry()).review(request)
    return request, record


def _policy() -> DependencyPolicy:
    return DependencyPolicy(
        policy_id="policy/software-factory/dependencies/v1",
        allowed_sources=frozenset({"pypi", "npm"}),
        allowed_licenses=frozenset({"License-Allowed"}),
        review_licenses=frozenset({"License-Review"}),
        blocked_licenses=frozenset({"License-Blocked"}),
    )


def _change(**overrides: object) -> DependencyChange:
    values: dict[str, object] = {
        "package": "example-dependency",
        "version": "1.2.3",
        "source": "pypi",
        "role": DependencyRole.DIRECT,
        "reason": "Required by the bounded integration implementation.",
        "integrity": "sha256:" + "d" * 64,
        "integrity_verified": True,
        "security_status": DependencySecurityStatus.CLEAR,
        "license": "License-Allowed",
        "commercial_compatibility": CommercialCompatibility.COMPATIBLE,
        "operation": DependencyOperation.ADD,
        "manifest_path": "pyproject.toml",
        "lockfile_path": "uv.lock",
    }
    values.update(overrides)
    return DependencyChange(**values)  # type: ignore[arg-type]


def _request(
    *,
    changes: tuple[DependencyChange, ...] | None = None,
    policy: DependencyPolicy | None = None,
    nonapproved_review: bool = False,
) -> DependencyGovernanceRequest:
    review_request, review_record = _review_bundle(nonapproved=nonapproved_review)
    return DependencyGovernanceRequest(
        governance_id="sf13-governance-1",
        review_request=review_request,
        review_record=review_record,  # type: ignore[arg-type]
        dependency_changes=(_change(),) if changes is None else changes,
        policy=policy or _policy(),
    )


def _governance() -> SoftwareFactoryDependencyGovernance:
    return SoftwareFactoryDependencyGovernance(_registry())


def test_complete_policy_compliant_dependency_is_allowed_without_authority() -> None:
    record = _governance().evaluate(_request())

    assert record.skill_id == "sf-dependency-governance"
    assert record.skill_version == "1.0.0"
    assert record.dependency_paths == ("pyproject.toml", "uv.lock")
    assert record.disposition is DependencyDisposition.ALLOW
    assert record.dependency_evidence[0].package == "example-dependency"
    assert record.dependency_evidence[0].role is DependencyRole.DIRECT
    assert record.dependency_evidence[0].security_status is DependencySecurityStatus.CLEAR
    assert record.dependency_evidence[0].commercial_compatibility is CommercialCompatibility.COMPATIBLE
    assert record.independent_review_required is True
    assert record.acceptance_authorized is False
    assert record.promotion_authorized is False
    assert record.deployment_authorized is False
    assert record.production_applied is False
    assert record.subject_mutated is False
    assert len(record.policy_sha256) == 64
    assert len(record.record_sha256) == 64


def test_manifest_or_lockfile_change_without_inventory_is_blocked() -> None:
    record = _governance().evaluate(_request(changes=()))

    assert record.disposition is DependencyDisposition.BLOCK
    assert record.dependency_evidence == ()
    assert record.policy_reasons == (
        "reviewed dependency manifest/lockfile changed without explained dependency inventory",
    )


def test_unexplained_or_unverified_dependency_addition_is_blocked() -> None:
    record = _governance().evaluate(
        _request(changes=(_change(reason="", integrity_verified=False),))
    )

    evidence = record.dependency_evidence[0]
    assert evidence.disposition is DependencyDisposition.BLOCK
    assert "dependency change has no business/technical reason" in evidence.policy_reasons
    assert "dependency integrity is not verified" in evidence.policy_reasons


def test_vulnerable_incompatible_or_unapproved_source_is_blocked() -> None:
    record = _governance().evaluate(
        _request(
            changes=(
                _change(
                    source="unapproved-registry",
                    security_status=DependencySecurityStatus.VULNERABLE,
                    commercial_compatibility=CommercialCompatibility.INCOMPATIBLE,
                ),
            )
        )
    )

    evidence = record.dependency_evidence[0]
    assert evidence.disposition is DependencyDisposition.BLOCK
    assert "dependency source is not allowlisted" in evidence.policy_reasons
    assert "dependency has a known vulnerable security status" in evidence.policy_reasons
    assert "dependency is commercially incompatible under supplied evidence" in evidence.policy_reasons


def test_license_policy_is_explicit_and_fail_closed() -> None:
    blocked = _governance().evaluate(
        _request(changes=(_change(license="License-Blocked"),))
    )
    assert blocked.disposition is DependencyDisposition.BLOCK

    review = _governance().evaluate(
        _request(changes=(_change(license="License-Review"),))
    )
    assert review.disposition is DependencyDisposition.REVIEW_REQUIRED

    unknown = _governance().evaluate(
        _request(changes=(_change(license="License-Unclassified"),))
    )
    assert unknown.disposition is DependencyDisposition.REVIEW_REQUIRED


def test_unknown_security_and_commercial_evidence_cannot_silently_allow() -> None:
    record = _governance().evaluate(
        _request(
            changes=(
                _change(
                    security_status=DependencySecurityStatus.UNKNOWN,
                    commercial_compatibility=CommercialCompatibility.UNKNOWN,
                ),
            )
        )
    )

    assert record.disposition is DependencyDisposition.REVIEW_REQUIRED
    assert "dependency security status is unknown" in record.dependency_evidence[0].policy_reasons
    assert "dependency commercial compatibility is unknown" in record.dependency_evidence[0].policy_reasons


def test_removing_a_complete_bad_dependency_is_not_blocked_by_its_old_risk_state() -> None:
    record = _governance().evaluate(
        _request(
            changes=(
                _change(
                    operation=DependencyOperation.REMOVE,
                    source="legacy-unapproved-source",
                    security_status=DependencySecurityStatus.VULNERABLE,
                    license="License-Blocked",
                    commercial_compatibility=CommercialCompatibility.INCOMPATIBLE,
                ),
            )
        )
    )

    assert record.disposition is DependencyDisposition.ALLOW
    assert record.dependency_evidence[0].policy_reasons == ()


def test_dependency_evidence_cannot_escape_reviewed_manifest_lock_scope() -> None:
    with pytest.raises(SoftwareFactoryError, match="exceeds reviewed dependency-path scope"):
        _governance().evaluate(
            _request(changes=(_change(manifest_path="apps/other/pyproject.toml"),))
        )


def test_stale_or_tampered_independent_review_is_rejected() -> None:
    request = _request()
    tampered = replace(request.review_record, record_sha256="f" * 64)

    with pytest.raises(SoftwareFactoryError, match="stale or tampered"):
        _governance().evaluate(replace(request, review_record=tampered))


def test_nonapproved_sf12_review_cannot_enter_dependency_governance() -> None:
    with pytest.raises(SoftwareFactoryError, match="completed, approved SF-12"):
        _governance().evaluate(_request(nonapproved_review=True))


def test_policy_cannot_default_unknown_evidence_to_allow_or_overlap_licenses() -> None:
    with pytest.raises(SoftwareFactoryError, match="cannot default to ALLOW"):
        _governance().evaluate(
            _request(
                policy=replace(
                    _policy(),
                    unknown_license_disposition=DependencyDisposition.ALLOW,
                )
            )
        )

    with pytest.raises(SoftwareFactoryError, match="must not overlap"):
        _governance().evaluate(
            _request(
                policy=replace(
                    _policy(),
                    blocked_licenses=frozenset({"License-Allowed"}),
                )
            )
        )


def test_governance_record_is_deterministic_for_identical_evidence() -> None:
    request = _request()
    first = _governance().evaluate(request)
    second = _governance().evaluate(request)

    assert first == second
    assert first.record_sha256 == second.record_sha256
    assert first.dependency_evidence[0].evidence_sha256 == second.dependency_evidence[0].evidence_sha256
